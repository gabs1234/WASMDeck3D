import taichi as ti
import taichi.math as tm # Use Taichi's math functions in kernels
import numpy as np # Still useful for initial data generation, some constants
import time

# --- Taichi Initialization ---
# Try Vulkan first, fallback to cuda, metal, cpu.
# You can force a specific backend e.g. ti.init(arch=ti.gpu) or ti.init(arch=ti.cpu)
# OpenGL backend often needed for ti.ui if others fail on some drivers.
try:
    ti.init(arch=ti.vulkan)
except:
    try:
        ti.init(arch=ti.cuda)
    except:
        try:
            ti.init(arch=ti.metal)
        except:
             try:
                 ti.init(arch=ti.opengl) # Good fallback for UI
             except:
                 ti.init(arch=ti.cpu)

print(f"Using Taichi backend: {ti.lang.impl.current_cfg().arch}")

@ti.data_oriented
class ParticleSimulationTaichi:
    def __init__(self, params):
        self.params = params
        self.num_particles = params.get('num_particles', 1000)
        self.domain_size = tm.vec3(params.get('domain_size', 20.0))
        self.domain_center = tm.vec3(params.get('domain_center', [0, 5, 0]))
        self.bounds_min = self.domain_center - self.domain_size / 2.0
        self.bounds_max = self.domain_center + self.domain_size / 2.0

        self.interaction_radius = ti.field(dtype=ti.f32, shape=())
        self.particle_radius = ti.field(dtype=ti.f32, shape=())
        self.gravity = ti.Vector.field(3, dtype=ti.f32, shape=())
        self.boundary_mode = params.get('boundary_mode', 'reflect') # String, used in Python logic
        self.collision_k = params.get('collision_spring_k', 10000.0)
        self.damping = params.get('damping', 0.999) # Velocity damping factor

        # Set constant simulation parameters (can be fields if they need to change)
        self.interaction_radius[None] = params.get('interaction_radius', 0.4)
        self.particle_radius[None] = params.get('particle_radius', 0.1)
        self.gravity[None] = tm.vec3(params.get('gravity', [0, -2.0, 0]))

        # Particle data fields
        self.positions = ti.Vector.field(3, dtype=ti.f32, shape=self.num_particles)
        self.velocities = ti.Vector.field(3, dtype=ti.f32, shape=self.num_particles)
        self.forces = ti.Vector.field(3, dtype=ti.f32, shape=self.num_particles)
        self.mass = ti.field(dtype=ti.f32, shape=self.num_particles)

        # --- Uniform Grid Setup ---
        # Cell size should be related to interaction radius for efficiency
        self.grid_cell_size = self.interaction_radius[None] * 2.0 # Common choice
        self.grid_dims = tm.ceil(self.domain_size / self.grid_cell_size).cast(int)
        self.num_grid_cells = self.grid_dims.x * self.grid_dims.y * self.grid_dims.z
        print(f"Grid dimensions: {self.grid_dims}, Total cells: {self.num_grid_cells}")

        # Grid data fields
        self.particle_grid_indices = ti.field(dtype=ti.i32, shape=self.num_particles) # Stores cell index for each particle
        self.particle_ids_sorted = ti.field(dtype=ti.i32, shape=self.num_particles) # Particle indices sorted by cell
        self.grid_cell_offsets = ti.field(dtype=ti.i32, shape=self.num_grid_cells + 1) # Start offset (+1 for end of last cell)

        # Allocate temporary storage for radix sort if needed (Taichi might handle internally)
        # self.sort_temp_keys = ti.field(dtype=ti.i32, shape=self.num_particles)
        # self.sort_temp_values = ti.field(dtype=ti.i32, shape=self.num_particles)

        # Initialize particles
        self.init_particles()

        # Visualization setup
        self.window = ti.ui.Window("Taichi Particle Simulation", (800, 800), vsync=True)
        self.canvas = self.window.get_canvas()
        self.scene = ti.ui.Scene()
        self.camera = ti.ui.Camera()
        self.camera.position(self.domain_center.x, self.domain_center.y, self.domain_center.z + self.domain_size.z * 1.2) # Adjust camera distance
        self.camera.lookat(self.domain_center.x, self.domain_center.y, self.domain_center.z)
        self.camera.up(0, 1, 0)


    @ti.kernel
    def init_particles(self):
        vel_range = self.params.get('initial_velocity_range', 3.0)
        for i in range(self.num_particles):
            # Initialize within bounds
            self.positions[i] = self.bounds_min + tm.rand(3) * self.domain_size
            self.velocities[i] = (tm.rand(3) * 2.0 - 1.0) * vel_range
            self.mass[i] = 1.0 # Assume uniform mass for simplicity
            self.forces[i] = tm.vec3(0.0)
            self.particle_ids_sorted[i] = i # Initialize sorted IDs


    @ti.func # Helper function usable within kernels
    def get_grid_cell_index(self, pos):
        """Calculates the 1D index for the grid cell containing pos."""
        grid_coord = tm.floor((pos - self.bounds_min) / self.grid_cell_size).cast(int)
        # Clamp coordinates to be within grid bounds (important for particles near max boundary)
        grid_coord = tm.clamp(grid_coord, 0, self.grid_dims - 1)
        # Convert 3D grid coord to 1D index
        return grid_coord.x + grid_coord.y * self.grid_dims.x + grid_coord.z * self.grid_dims.x * self.grid_dims.y

    @ti.kernel
    def update_grid(self):
        # 1. Calculate cell index for each particle
        for i in range(self.num_particles):
            self.particle_grid_indices[i] = self.get_grid_cell_index(self.positions[i])
            self.particle_ids_sorted[i] = i # Reset value array for sorting

        # 2. Sort particle IDs based on their cell indices
        #    Taichi's sort_pairs sorts keys (grid indices) and permutes values (particle ids)
        #    NOTE: Requires Taichi >= 1.6.0 for built-in radix sort supporting pairs
        #    If using older Taichi, you might need a custom radix sort implementation.
        ti.algorithms.custom_radix_sort_pairs(keys=self.particle_grid_indices, values=self.particle_ids_sorted)
        # If sort is not available or you prefer manual: implement counting sort or radix sort logic here.


        # 3. Calculate cell offsets (prefix sum)
        self.grid_cell_offsets.fill(0) # Reset offsets/counts
        # Count particles per cell (using the *sorted* indices)
        for i in range(self.num_particles):
            cell_idx = self.particle_grid_indices[i] # Get cell index from sorted key array
            # Atomic add is needed because multiple threads might update the same cell count
            ti.atomic_add(self.grid_cell_offsets[cell_idx + 1], 1) # Use cell_idx+1 for prefix sum logic

        # Perform prefix sum (exclusive scan) on counts to get offsets
        # This can be done with Taichi's scan algorithms or manually
        # Manual sequential prefix sum (can be parallelized too)
        for i in range(self.num_grid_cells):
            self.grid_cell_offsets[i+1] += self.grid_cell_offsets[i]
        # Now grid_cell_offsets[cell_idx] is the start index in particle_ids_sorted
        # and grid_cell_offsets[cell_idx+1] is the end index (exclusive)

    @ti.kernel
    def calculate_forces(self):
        # Clear forces from previous step
        for i in range(self.num_particles):
            self.forces[i] = self.gravity[None] * self.mass[i]

        inter_radius_sq = self.interaction_radius[None]**2
        min_dist_particle = self.particle_radius[None] * 2.0
        min_dist_sq = min_dist_particle * min_dist_particle

        # Iterate through each particle ('p_idx' is the ORIGINAL particle index)
        for p_idx_orig in range(self.num_particles):
            pos_p = self.positions[p_idx_orig]
            mass_p = self.mass[p_idx_orig]
            force_p = tm.vec3(0.0) # Accumulate interaction forces locally

            # Get grid cell coordinates of particle p
            grid_coord_p = tm.floor((pos_p - self.bounds_min) / self.grid_cell_size).cast(int)

            # Iterate through the 3x3x3 neighboring cells (including p's own cell)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    for dz in range(-1, 2):
                        neighbor_grid_coord = grid_coord_p + tm.ivec3(dx, dy, dz)

                        # Check if neighbor cell is within grid bounds
                        if (tm.all(neighbor_grid_coord >= 0) and
                            tm.all(neighbor_grid_coord < self.grid_dims)):

                            # Get 1D index of neighbor cell
                            neighbor_cell_idx = neighbor_grid_coord.x + \
                                                neighbor_grid_coord.y * self.grid_dims.x + \
                                                neighbor_grid_coord.z * self.grid_dims.x * self.grid_dims.y

                            # Get start and end indices for particles in this neighbor cell
                            start_idx = self.grid_cell_offsets[neighbor_cell_idx]
                            end_idx = self.grid_cell_offsets[neighbor_cell_idx + 1]

                            # Iterate through particles ('n_sorted_idx') in the neighbor cell
                            for n_sorted_idx in range(start_idx, end_idx):
                                # Get the ORIGINAL index ('n_idx_orig') of the neighbor particle
                                n_idx_orig = self.particle_ids_sorted[n_sorted_idx]

                                # Don't interact with self
                                if p_idx_orig == n_idx_orig:
                                    continue

                                pos_n = self.positions[n_idx_orig]
                                dist_vec = pos_n - pos_p
                                dist_sq = tm.length_sq(dist_vec)

                                # Check if within interaction radius AND potential collision
                                if dist_sq < inter_radius_sq and dist_sq > 1e-9: # Avoid division by zero
                                    # Collision check (simple spring repulsion)
                                    if dist_sq < min_dist_sq:
                                        dist = tm.sqrt(dist_sq)
                                        overlap = min_dist_particle - dist
                                        force_dir = dist_vec / dist
                                        repulsion_force = force_dir * self.collision_k * overlap * 0.5 # Share force
                                        force_p -= repulsion_force

                                    # --- Add other forces here (e.g., Lennard-Jones, attraction) ---


            # Atomically add the locally accumulated forces to the global force field
            # This is needed if multiple threads writing forces for DIFFERENT p_idx_orig
            # based on neighbors could potentially conflict (less likely with this structure).
            # Safer to use atomic add, though direct add might work depending on Taichi scheduling.
            # Correction: Since each outer loop iteration calculates force for *one* specific
            # p_idx_orig, writing directly to self.forces[p_idx_orig] should be safe.
            self.forces[p_idx_orig] += force_p


    @ti.kernel
    def update_particles(self, dt: ti.f32):
        # Update velocities and positions
        for i in range(self.num_particles):
            acceleration = self.forces[i] / self.mass[i]
            new_velocity = self.velocities[i] + acceleration * dt
            self.velocities[i] = new_velocity * self.damping # Apply damping
            self.positions[i] += self.velocities[i] * dt

            # Boundary conditions
            if self.boundary_mode == 'reflect':
                for d in ti.static(range(3)): # ti.static unfolds loop for each dimension
                    if self.positions[i][d] < self.bounds_min[d]:
                        self.positions[i][d] = self.bounds_min[d] + (self.bounds_min[d] - self.positions[i][d]) * 0.5 # Less bouncy reflection
                        self.velocities[i][d] *= -0.5 # Reflect velocity, dampen
                    elif self.positions[i][d] > self.bounds_max[d]:
                        self.positions[i][d] = self.bounds_max[d] - (self.positions[i][d] - self.bounds_max[d]) * 0.5
                        self.velocities[i][d] *= -0.5

            elif self.boundary_mode == 'wrap':
                 for d in ti.static(range(3)):
                     if self.positions[i][d] < self.bounds_min[d]:
                         self.positions[i][d] += self.domain_size[d]
                     elif self.positions[i][d] > self.bounds_max[d]:
                          self.positions[i][d] -= self.domain_size[d]


    def step(self, dt):
        """Performs one simulation step."""
        # 1. Update the spatial grid based on current positions
        self.update_grid()
        # 2. Calculate forces based on neighbors found via the grid
        self.calculate_forces()
        # 3. Update particle positions and velocities
        self.update_particles(dt)

    def run_visualization(self, dt=0.01, steps_per_frame=1):
        """Runs the simulation loop with ti.ui visualization."""
        frame = 0
        last_time = time.time()

        while self.window.running:
            # Run simulation steps
            for _ in range(steps_per_frame):
                self.step(dt)

            # Setup scene
            self.scene.set_camera(self.camera)
            self.scene.ambient_light((0.5, 0.5, 0.5))
            # Point light source for better shading
            self.scene.point_light(pos=(self.domain_center.x + self.domain_size.x,
                                        self.domain_center.y + self.domain_size.y,
                                        self.domain_center.z + self.domain_size.z),
                                   color=(1, 1, 1))

            # Draw particles
            self.scene.particles(self.positions, radius=self.particle_radius[None], color=(0.2, 0.6, 1.0))

            # Draw bounding box (optional)
            box_corners = np.array([
                [self.bounds_min[0], self.bounds_min[1], self.bounds_min[2]],
                [self.bounds_max[0], self.bounds_min[1], self.bounds_min[2]],
                [self.bounds_max[0], self.bounds_max[1], self.bounds_min[2]],
                [self.bounds_min[0], self.bounds_max[1], self.bounds_min[2]],
                [self.bounds_min[0], self.bounds_min[1], self.bounds_max[2]],
                [self.bounds_max[0], self.bounds_min[1], self.bounds_max[2]],
                [self.bounds_max[0], self.bounds_max[1], self.bounds_max[2]],
                [self.bounds_min[0], self.bounds_max[1], self.bounds_max[2]],
            ])
            box_lines_indices = np.array([
                [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
                [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
                [0, 4], [1, 5], [2, 6], [3, 7]   # Connecting edges
            ], dtype=np.int32)
            self.scene.lines(ti.Vector.field(3,ti.f32, shape=box_corners.shape[0]),
                             indices=ti.field(ti.i32, shape=box_lines_indices.shape[0]*2),
                             color=(0.8, 0.8, 0.8), width=1.0)
            # Need to copy data to the fields for lines (ti.ui limitation sometimes)
            # Possible bug/feature: scene.lines might expect fields directly
            box_corners_field = ti.Vector.field(3, ti.f32, shape=box_corners.shape[0])
            box_lines_indices_field = ti.field(ti.i32, shape=box_lines_indices.flatten().shape[0])
            box_corners_field.from_numpy(box_corners)
            box_lines_indices_field.from_numpy(box_lines_indices.flatten())
            self.scene.lines(box_corners_field, indices=box_lines_indices_field, color=(0.8, 0.8, 0.8), width=1.0)

            # Render the scene
            self.canvas.scene(self.scene)
            self.window.show()

            frame += 1
            current_time = time.time()
            if current_time - last_time >= 1.0:
                fps = frame / (current_time - last_time)
                print(f"FPS: {fps:.2f}")
                frame = 0
                last_time = current_time


# --- Example Usage ---
if __name__ == "__main__":
    sim_params = {
        'num_particles': 20000,        # Can handle much more now!
        'domain_size': [20.0, 20.0, 20.0],
        'domain_center': [0, 10, 0],   # Start particles higher
        'gravity': [0, -5.0, 0],       # Adjusted gravity
        'interaction_radius': 0.4,     # Interaction check radius
        'particle_radius': 0.05,        # Visual radius
        'boundary_mode': 'reflect',    # 'reflect' or 'wrap'
        'initial_velocity_range': 5.0,
        'collision_spring_k': 20000.0, # Stiffness of collision
        'damping': 0.99                 # Velocity damping
    }

    simulation = ParticleSimulationTaichi(sim_params)

    # Run with visualization
    simulation.run_visualization(dt=0.01, steps_per_frame=2) # Adjust dt and steps_per_frame