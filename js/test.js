import { loadSimulation } from './loader.js';

const startApp = async () => {
  console.log("[main] Loading Pyodide...");
  const pyodide = await loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.23.3/full/",
  });

  await pyodide.loadPackage('numpy');
  await loadSimulation(pyodide);

  console.log("[main] Starting p5.js sketch...");

  new p5((sketch) => {

    let canvasWidth = 800;
    let canvasHeight = 600;
    let coulombclass;
    let coulombclassInstance;
    let paused = false;
    let particles = [];
    let particlePaths = [];

    // KE-to-Color settings
    let minKe = 0, maxKe = 50;
    let lowKeHue = 240, highKeHue = 0;

    let simulation_params = {
      n_particles: 150,
      n_charges: 3,
      charge_strength: 5000,
      charge_radius: 16,
      particle_radius: 8
    };

    function getKeColor(ke, alpha = 150) {
      let cKe = sketch.constrain(ke, minKe, maxKe);
      let hue = sketch.map(cKe, minKe, maxKe, lowKeHue, highKeHue);
      return sketch.color(hue, 90, 90, alpha/255);
    }

    sketch.setup = function () {
      const container = document.getElementById('interactive');
      if (!container) return;
      canvasWidth = container.clientWidth;
      canvasHeight = container.clientHeight;
      this.createCanvas(canvasWidth, canvasHeight).parent('interactive');
      this.colorMode(this.HSB, 360, 100, 100, 1);
      this.ellipseMode(this.RADIUS);
      this.background(0, 0, 15);

      try {
        coulombclass = pyodide.globals.get("Coulomb");
        if (!coulombclass) throw new Error("Coulomb class not found");
        // Convert JS object to Python dict for constructor
        const simParamsPy = pyodide.toPy(simulation_params);
        coulombclassInstance = coulombclass(canvasWidth, canvasHeight, simParamsPy);
        console.log("Python Coulomb simulation initialized");

        // Initialize empty paths
        particlePaths = Array(simulation_params.n_particles).fill().map(() => []);
      } catch (e) {
        console.error("Error initializing simulation:", e);
      }
    };

    sketch.draw = function () {
      this.background(0, 0, 15);
      if (!paused && coulombclassInstance) {
        try {
          const dt = sketch.deltaTime / 1000;
          let proxy = coulombclassInstance.update(dt);
          particles = proxy.toJs({ create_proxies: false, depth: 2 });
          proxy.destroy();

          particles.forEach((p, i) => {
            if (Array.isArray(p) && p.length === 3) {
              const [x, y, ke] = p;
              if (!isNaN(x) && !isNaN(y) && !isNaN(ke)) {
                particlePaths[i].push({ pos: sketch.createVector(x, y), ke });
              }
            }
          });
        } catch (err) {
          console.error("Simulation update error:", err);
          paused = true;
        }
      }

      // Draw charges
      if (coulombclassInstance) {
        let charges = coulombclassInstance.get_charges().toJs({ depth: 2 });
        charges.forEach(([x, y, q]) => {
          sketch.fill(q > 0 ? sketch.color(0,100,100) : sketch.color(240,100,100));
          sketch.noStroke();
          sketch.ellipse(x, y, simulation_params.charge_radius, simulation_params.charge_radius);
        });
      }

      // Draw paths
      sketch.noFill();
      sketch.strokeWeight(1.5);
      particlePaths.forEach(path => {
        for (let j = 1; j < path.length; j++) {
          const prev = path[j-1], curr = path[j];
          if (prev && curr) {
            sketch.stroke(getKeColor(curr.ke, 150));
            sketch.line(prev.pos.x, prev.pos.y, curr.pos.x, curr.pos.y);
          }
        }
      });

      // Draw particles
      sketch.noStroke();
      particles.forEach(p => {
        if (Array.isArray(p) && p.length === 3) {
          const [x, y, ke] = p;
          let col = getKeColor(ke, 200);
          sketch.fill(sketch.hue(col), sketch.saturation(col), 100);
          sketch.ellipse(x, y, simulation_params.particle_radius, simulation_params.particle_radius);
        }
      });
    };
  });
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startApp);
} else {
  startApp();
}