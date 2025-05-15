const python_filename = "./python/main.py"; // Adjust path if needed
let python_code = null;
let pyodide = null;
let simInstance = null;

let containerDiv = null;
let canvasWidth = 600; // Default fallback
let canvasHeight = 400; // Default fallback

// Keep simulation parameters in JS for easy tweaking
let simulation_params = {
	"n_particles": 150,          // Number of particles
	"n_charges": 3,              // Number of fixed charges
	"charge_strength": 5000,     // Scales the force strength (adjust as needed)
	"charge_radius": 8,          // Visual size in pixels
	"particle_radius": 3         // Visual size in pixels
	// "particle_mass": 1 // Add if implementing velocity/acceleration
};

// p5.js preload function
function preload() {
	console.log("Preloading resources...");

	containerDiv = document.getElementById('interactive');
	if (!containerDiv) {
		console.error("Fatal Error: Could not find div with id='interactive'");
		return;
	}
	// Use clientWidth/clientHeight for actual rendered size
	canvasWidth = containerDiv.clientWidth || canvasWidth;
	canvasHeight = containerDiv.clientHeight || canvasHeight;

	// Load the Python code
	python_code = loadString(python_filename);
	console.log(`Python code loaded from ${python_filename}`);

	// Load Pyodide
	console.log("Loading Pyodide...");
	try {
		// Check if pyodide is already loaded (e.g., in development with hot-reloading)
		if (typeof loadPyodide === 'function') {
			pyodide = await loadPyodide();
			console.log("Pyodide loaded.");
		} else {
			console.error("loadPyodide function not found. Make sure Pyodide script is included before this script.");
			return;
		}
	} catch (error) {
		console.error("Error loading Pyodide:", error);
		return; // Stop if Pyodide fails to load
	}


	// Load numpy and run Python code
	console.log("Loading NumPy and Python simulation code...");
	try {
		await pyodide.loadPackage("numpy");
		// await pyodide.loadPackage("micropip"); // micropip not needed if numpy is standard
		// const micropip = pyodide.pyimport("micropip");
		// await micropip.install("numpy"); // Use loadPackage directly if possible
		await pyodide.runPythonAsync(python_code);
		console.log("NumPy loaded and Python code executed.");
	} catch (error) {
		console.error("Error loading packages or running Python code:", error);
		pyodide = null; // Mark pyodide as failed
	}
}

// p5.js setup function
function setup() {
	// Ensure preload finished successfully
	if (!pyodide || !python_code) {
		console.error("Pyodide or Python code not ready. Cannot setup.");
		createCanvas(canvasWidth, canvasHeight); // Create a canvas to show error
		background(100);
		fill(255, 0, 0);
		textAlign(CENTER, CENTER);
		textSize(16);
		text("Error during initialization. Check console.", width / 2, height / 2);
		noLoop(); // Stop draw loop
		return;
	}

	let canvas = createCanvas(canvasWidth, canvasHeight);
	canvas.parent('interactive'); // Attach canvas to the div
	console.log(`Canvas created ${canvasWidth}x${canvasHeight} inside #interactive`);

	// Set up the simulation
	console.log("Initializing Python simulation...");
	try {
		// Get the Python class
		const CoulombClass = pyodide.globals.get('Coulomb');
		if (!CoulombClass) {
			throw new Error("Python 'Coulomb' class not found in global scope.");
		}

		// Convert JS params object to Python dict implicitly
		// Pass width, height, and params object
		simInstance = CoulombClass(canvasWidth, canvasHeight, simulation_params);
		if (!simInstance) {
			throw new Error("Failed to create Python simulation instance.");
		}
		console.log("Python Simulation instance created.");

		// --- CRITICAL: Fetch initial state FROM Python ---
		// Use depth: 2 for lists/tuples of lists/tuples (or NumPy arrays)
		const initialChargesPy = simInstance.get_charges();
		charges = initialChargesPy.toJs({ depth: 2 });
		initialChargesPy.destroy(); // Release memory for the proxy

		const initialParticlesPy = simInstance.get_particles();
		particles = initialParticlesPy.toJs({ depth: 2 });
		initialParticlesPy.destroy(); // Release memory for the proxy

		console.log(`Workspaceed initial state: ${charges.length} charges, ${particles.length} particles.`);

	} catch (error) {
		console.error("Error during simulation setup:", error);
		background(100); fill(255, 0, 0); textAlign(CENTER, CENTER); textSize(16);
		text(`Simulation Setup Error:\n${error.message}`, width / 2, height / 2);
		noLoop(); // Stop draw loop on error
	}
}

function draw_particles() {
	if (!particles || particles.length === 0) return;
	noStroke();
	fill(0, 100, 255, 200); // Blueish, slightly transparent
	const radius = simulation_params.particle_radius || 3;
	for (const p of particles) {
		// p is expected to be [x, y]
		if (p && typeof p[0] === 'number' && typeof p[1] === 'number') {
			ellipse(p[0], p[1], radius * 2);
		} else {
			// console.warn("Invalid particle data:", p); // Avoid flooding console
		}
	}
}

function draw_charges() {
	if (!charges || charges.length === 0) return;
	noStroke();
	const radius = simulation_params.charge_radius || 5;
	for (const c of charges) {

		fill('green'); 
		ellipse(c[0], c[1], radius * 2);
	}
}

// p5.js draw loop
function draw() {
	// Check if the simulation instance is ready
	if (!simInstance || !particles) {
		background(150);
		fill(255);
		textAlign(CENTER, CENTER);
		text("Simulation initializing or failed...", width / 2, height / 2);
		return; // Wait until setup is complete
	}

	// Time step in seconds
	let dt = deltaTime / 1000.0;

	// Prevent issues with large steps if tab is inactive/lag occurs
	dt = Math.min(dt, 0.05); // Clamp dt to max 50ms (adjust as needed)

	if (dt <= 0) return; // Avoid zero or negative dt

	// Update simulation in Python
	try {
		// Call update and get the updated particles (as a PyProxy)
		const updatedParticlesPy = simInstance.update(dt);

		// --- CRITICAL: Update JS particles array ---
		// Convert the PyProxy result back to a JS array
		particles = updatedParticlesPy.toJs({ depth: 2 });

		// IMPORTANT: Destroy the proxy to free memory in Pyodide/Wasm
		updatedParticlesPy.destroy();

	} catch (error) {
		console.error("Error during simulation update:", error);
		fill(255, 0, 0); textAlign(LEFT, TOP); text(`Update Error: ${error.message}`, 10, 10);
		noLoop(); // Stop the loop on error
		return;
	}

	// --- Drawing ---
	background(240); // Light grey background

	// Draw particles and charges
	draw_charges(); // Draw charges first (usually static)
	draw_particles(); // Draw particles on top

	// Optional: Display frame rate or particle count
	// fill(0);
	// text(`FPS: ${frameRate().toFixed(1)}`, 10, 20);
	// text(`Particles: ${particles.length}`, 10, 40);
}