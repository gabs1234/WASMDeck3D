# Reveal.js Interactive Presentation Template

This project serves as a template for creating Reveal.js presentations that leverage modern web technologies like WebAssembly (WASM) via Pyodide (for Python) and Emscripten (for C/C++), and WebGL libraries like p5.js and Three.js for interactive 2D/3D content.

## Overview

The goal of this template is to provide a starting point for developers and educators who want to create engaging, interactive presentations by embedding complex simulations, visualizations, or computations directly into their slides.

## Features

*   **Reveal.js Framework**: For creating beautiful and navigable slideshows.
*   **Pandoc Integration**: For generating presentations from Markdown.
*   **Makefile-based Build System**: Simplifies the build process.
*   **Pyodide (Python via WASM)**: Allows running Python code directly in the browser. Includes examples with NumPy.
*   **Emscripten (C/C++ via WASM)**: Demonstrates how to compile C code to WASM and use it in JavaScript.
*   **p5.js Integration**: For 2D interactive graphics and animations.
*   **Three.js Setup**: Basic import map configuration for 3D graphics (further implementation example needed).
*   **Customizable Themes and Styles**: Easily change the look and feel.
*   **Interactive Examples**: Demonstrates embedding p5.js sketches that interact with Python (Pyodide) and C (WASM) code.

## Project Structure

```
.
├── c/                            # C/C++ source files for WASM compilation
│   └── main.c                    # Example C code
├── custom-revealjs-template.html # Pandoc HTML template for Reveal.js
├── header.html                   # Included in <head> of slides.html (for scripts, CSS links)
├── images/                       # Images used in the presentation
├── include-after.html            # Included after <body> of slides.html
├── include-before.html           # Included before <body> of slides.html (e.g., importmaps)
├── index.html                    # Alternative: Simpler Reveal.js setup directly from Markdown
├── js/                           # JavaScript files
│   ├── field.js                  # Example p5.js sketch with Pyodide
│   ├── loader.js                 # Helper to load Python simulation code
│   └── test.js                   # Main interactive p5.js + Pyodide + C/WASM example
├── lib/                          # Local libraries (if any, e.g. p5.min.js, pyodide distribution)
├── main.ipynb                    # Jupyter notebook (e.g., for experiments, not part of build)
├── makefile                      # Makefile for building the presentation
├── python/                       # Python files for Pyodide
│   ├── main.py                   # Example Python code for js/field.js
│   └── test.py                   # Example Python code (Coulomb class) for js/test.js
├── slides.html                   # Generated presentation (output of 'make build')
├── slides.md                     # Markdown source for the presentation content
├── style.css                     # Custom CSS styles
└── README.md                     # This file
```

## Getting Started

### Prerequisites

*   **Pandoc**: Required for converting Markdown to Reveal.js HTML. Install from [pandoc.org](https://pandoc.org/installing.html).
*   **Make**: For using the Makefile to build the presentation. Commonly available on Linux/macOS. Windows users might need to install it (e.g., via Chocolatey or WSL).
*   **Web Server**: To serve the presentation locally, as some features (like WASM loading) might not work correctly when opened directly from the file system (`file:///`). Python's `http.server` or Node.js `http-server` are good options.

### Building the Presentation

1.  **Clone the repository** (or use it as a template).
2.  **Navigate to the project directory**.
3.  **Run the build command**:
    ```bash
    make build
    ```
    This will generate `slides.html` from `slides.md` using the `custom-revealjs-template.html`.

4.  **Serve the presentation**:
    Using Python:
    ```bash
    python -m http.server
    ```
    Then open `http://localhost:8000/slides.html` (or your generated `slides.html`) in your browser.

### Customizing Content

1.  **Edit `slides.md`**: This is where you write your presentation content using Markdown.
    *   New slides are typically started by a level 1, 2, or 3 heading (configurable in `makefile` via `SLIDE_LEVEL`).
    *   Vertical slides can be created using `----` (or as configured in Reveal.js).
2.  **Modify `style.css`**: Add your custom styles here.
3.  **Update `makefile` variables**:
    *   `INPUT`: Input Markdown file (default: `slides.md`).
    *   `OUTPUT`: Output HTML file (default: `slides.html`).
    *   `THEME`: Reveal.js theme (default: `black`). See Reveal.js documentation for available themes.
    *   `TRANSITION`: Slide transition style (default: `slide`).
    *   And others like `REVEAL_URL`, `HIGHLIGHT_STYLE`.

### Adding Interactive Elements

*   **Python (Pyodide)**:
    1.  Write your Python code in the `python/` directory.
    2.  Load and run it in your JavaScript files (see `js/test.js` and `js/loader.js` for examples).
    3.  Ensure Pyodide and any necessary Python packages are loaded (see `header.html` and `js/test.js`).
*   **C/C++ (Emscripten WASM)**:
    1.  Write your C/C++ code in the `c/` directory.
    2.  Compile it to WASM using Emscripten. For example:
        ```bash
        emcc c/main.c -o js/c_module.js -s EXPORTED_FUNCTIONS="['_compute_field', '_set_charges']" -s EXPORTED_RUNTIME_METHODS="['ccall', 'cwrap']"
        ```
        (You'll need to have Emscripten SDK installed and configured).
    3.  Call the WASM functions from your JavaScript (see `js/test.js` for an example of how it *could* be integrated, though the direct C call example is not fully fleshed out in `test.js` but the C code exists).
*   **p5.js**:
    1.  Create your p5.js sketches in the `js/` directory.
    2.  Include the p5.js library (see `header.html`).
    3.  Embed your sketch in a slide, typically by creating a `div` container in `slides.md` and having your p5.js script target that `div` (see `slides.md` and `js/test.js` which targets `<div id="interactive">`).
*   **Three.js**:
    1.  The `include-before.html` file sets up an import map for Three.js.
    2.  You can then import Three.js modules in your JavaScript files:
        ```javascript
        import * as THREE from 'three';
        // Your Three.js code here
        ```
    3.  Create a canvas or container in your slide and render your Three.js scene there.

## Key Files for Customization

*   **`slides.md`**: Your primary content file.
*   **`style.css`**: For custom styling.
*   **`custom-revealjs-template.html`**: If you need to change the core HTML structure, Reveal.js initialization options, or global script/plugin loading.
*   **`header.html`**: Add global CSS or JS links/scripts that need to be in the `<head>`.
*   **`include-before.html` / `include-after.html`**: For scripts or HTML to be included right after `<body>` or before `</body>`.
*   **`js/` directory**: For your custom JavaScript, p5.js sketches, and WASM interactions.
*   **`python/` directory**: For Python scripts to be run with Pyodide.
*   **`c/` directory**: For C/C++ source code to be compiled to WASM.

## Technologies Used

*   [Reveal.js](https://revealjs.com/)
*   [Pandoc](https://pandoc.org/)
*   [Pyodide](https://pyodide.org/)
*   [Emscripten](https://emscripten.org/) (for C/C++ to WASM)
*   [p5.js](https://p5js.org/)
*   [Three.js](https://threejs.org/) (setup included)

## Alternative Simple Setup: `index.html`

The `index.html` file provides a simpler way to get started if you don't want to use Pandoc or Make. It loads `slides.md` directly using the Reveal.js Markdown plugin.

To use it:
1.  Edit `slides.md`.
2.  Serve the project directory using a local web server.
3.  Open `http://localhost:PORT/index.html` in your browser.

This method is quicker for simple presentations but offers less control over the Reveal.js initialization and HTML structure compared to the Pandoc/Makefile approach.

## Future Enhancements / TODO for Template Users

*   Add a more complete Three.js example integrated into a slide.
*   Provide a clearer example of calling the C WASM module from `js/test.js`.
*   Document the Emscripten compilation command more prominently.
*   Consider adding a live-reloading development server setup.

---

This template is designed to be a flexible foundation. Feel free to adapt and extend it to suit your specific interactive presentation needs!
