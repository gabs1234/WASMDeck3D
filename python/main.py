import numpy as np
import random # Keep random for choice if needed, but NumPy's is often preferred

class Coulomb:
    def __init__(self, width, height, params):
        """
        Initializes the simulation using NumPy arrays.
        """
        self.width = width
        self.height = height
        self.params = params
        self.k = params.get('charge_strength', 1.0) # Coulomb's constant / scaling factor

        rng = np.random.default_rng()

        # Initialize charges as NumPy array: [[x1, y1, q1], [x2, y2, q2], ...]
        n_charges = int(params.get('n_charges', 1)) # Ensure integer
        self.charges = np.zeros((n_charges, 3))
        self.charges[:, 0] = rng.uniform(0, width, size=n_charges)  # x positions
        self.charges[:, 1] = rng.uniform(0, height, size=n_charges) # y positions
        self.charges[:, 2] = rng.choice([-1, 1], size=n_charges)    # charge value

        # Initialize particles as NumPy array: [[x1, y1], [x2, y2], ...]
        n_particles = int(params.get('n_particles', 100)) # Ensure integer
        self.particles = np.zeros((n_particles, 2))
        self.particles[:, 0] = rng.uniform(0, width, size=n_particles)  # x positions
        self.particles[:, 1] = rng.uniform(0, height, size=n_particles) # y positions
        
        # Add velocities for more realistic motion (optional but recommended)
        # self.velocities = np.zeros_like(self.particles) 
        # Consider adding mass from params if using velocity/acceleration


    def get_particles(self):
        """Returns the current particle positions as a NumPy array."""
        return self.particles

    def get_charges(self):
        """Returns the charge data as a NumPy array."""
        return self.charges

    def update(self, dt):
        """
        Updates the positions of the particles based on Coulomb forces using NumPy.
        Assumes particle charge is +1 for simplicity.
        """
        if self.particles.shape[0] == 0 or self.charges.shape[0] == 0:
             return self.particles # Nothing to do

        # Expand dimensions for broadcasting:
        # particles: (N, 1, 2) -> [[x_p1, y_p1]], [[x_p2, y_p2]], ...
        # charges:   (1, M, 3) -> [[[x_c1, y_c1, q_c1], [x_c2, y_c2, q_c2], ...]]
        p_pos = self.particles[:, np.newaxis, :] # Shape (N, 1, 2)
        c_pos = self.charges[np.newaxis, :, :2]  # Shape (1, M, 2)
        c_q = self.charges[np.newaxis, :, 2]     # Shape (1, M)

        # Calculate displacement vectors (dx, dy) from each charge to each particle
        # Broadcasting happens here: (N, 1, 2) - (1, M, 2) -> (N, M, 2)
        delta_pos = p_pos - c_pos # Vector from charge TO particle

        # Calculate distances squared: dx^2 + dy^2
        # Sum over the last axis (axis=2) -> (N, M)
        r_sq = np.sum(delta_pos**2, axis=2)

        # Avoid division by zero if a particle is exactly on a charge
        # Add a small epsilon or handle cases where r_sq is very small
        epsilon = 1e-6 
        r_sq = np.maximum(r_sq, epsilon) # Prevent division by zero or tiny distances

        # Calculate distance r = sqrt(r_sq) -> (N, M)
        r = np.sqrt(r_sq)

        # Calculate force magnitude: F = k * q_charge * q_particle / r^2
        # Assuming q_particle = +1
        # Force is repulsive if q_charge is positive, attractive if negative
        # Shape: (1, M) / (N, M) -> (N, M)
        f_mag = -self.k * c_q / r_sq # Negative sign because delta_pos is charge->particle

        # Calculate force vectors (Fx, Fy)
        # Force direction is delta_pos / r (unit vector from charge to particle)
        # F_vector = F_mag * (delta_pos / r)
        # Need to reshape f_mag to (N, M, 1) for broadcasting with delta_pos (N, M, 2)
        f_vectors = f_mag[:, :, np.newaxis] * (delta_pos / r[:, :, np.newaxis]) # Shape (N, M, 2)

        # Sum forces from all charges acting on each particle
        # Sum over axis=1 (charges) -> (N, 2)
        total_force = np.sum(f_vectors, axis=1)

        # Update particle positions using Euler's method
        # pos_new = pos_old + force * dt (ignoring mass for simplicity, force acts like acceleration)
        self.particles += total_force * dt

        # --- Boundary Conditions (Wrap around) ---
        # Wrap X
        self.particles[:, 0] = np.mod(self.particles[:, 0], self.width)
        # Wrap Y
        self.particles[:, 1] = np.mod(self.particles[:, 1], self.height)

        # --- Boundary Conditions (Reflection - Alternative) ---
        # particles_x = self.particles[:, 0]
        # particles_y = self.particles[:, 1]
        # # Reflect X
        # mask_x_over = particles_x > self.width
        # particles_x[mask_x_over] = 2 * self.width - particles_x[mask_x_over]
        # mask_x_under = particles_x < 0
        # particles_x[mask_x_under] = -particles_x[mask_x_under]
        # # Reflect Y
        # mask_y_over = particles_y > self.height
        # particles_y[mask_y_over] = 2 * self.height - particles_y[mask_y_over]
        # mask_y_under = particles_y < 0
        # particles_y[mask_y_under] = -particles_y[mask_y_under]
        # self.particles[:, 0] = particles_x
        # self.particles[:, 1] = particles_y
        
        # --- Update velocities if using them ---
        # acceleration = total_force / self.params['particle_mass'] # If mass is used
        # self.velocities += acceleration * dt
        # self.particles += self.velocities * dt
        # # Add velocity reflection for reflection boundary conditions

        return self.particles # Return updated positions