export async function loadSimulation(pyodide) {
    const response = await fetch('../python/test.py');
    const code = await response.text();
    pyodide.runPython(code);
    console.log("[simulation] Python simulation loaded.");
  }
  