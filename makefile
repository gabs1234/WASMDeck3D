# Makefile for building Reveal.js presentations via Pandoc

# Default configuration variables:
# You can modify these directly or override via command line (e.g. make build THEME=moon)
INPUT          = slides.md                # Input Markdown file.
OUTPUT         = slides.html              # Output HTML file.
THEME          = black                    # Reveal.js theme (e.g., black, white, league, etc.).
REVEAL_URL     = https://cdn.jsdelivr.net/npm/reveal.js  # URL to load Reveal.js.
SLIDE_LEVEL    = 3                       # Markdown heading level that starts a new slide.
CSS_FILE       = style.css                # Custom CSS file for additional styling.
TRANSITION     = slide                    # Slide transition type (fade, slide, convex, concave, none).
HIGHLIGHT_STYLE= tango                    # Code syntax highlighting style (can be any supported by Pandoc).

.PHONY: help build clean

help:
	@echo "Pandoc Reveal.js Presentation Makefile"
	@echo "========================================"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help           Show this help message"
	@echo "  build          Build the presentation using Pandoc"
	@echo "  clean          Remove generated output"
	@echo ""
	@echo "Customizable Variables (modify in the Makefile or override at the command line):"
	@echo "  INPUT          Input Markdown file (default: $(INPUT))"
	@echo "  OUTPUT         Output HTML file (default: $(OUTPUT))"
	@echo "  THEME          Reveal.js theme (default: $(THEME))"
	@echo "  REVEAL_URL     URL to Reveal.js (default: $(REVEAL_URL))"
	@echo "  SLIDE_LEVEL    Heading level for new slides (default: $(SLIDE_LEVEL))"
	@echo "  CSS_FILE       Custom CSS file (default: $(CSS_FILE))"
	@echo "  TRANSITION     Slide transition type (default: $(TRANSITION))"
	@echo "  HIGHLIGHT_STYLE Code syntax highlighting style (default: $(HIGHLIGHT_STYLE))"
	@echo ""
	@echo "Example: make build THEME=moon SLIDE_LEVEL=1"
	@echo ""

build:
	@echo "Building presentation from $(INPUT) to $(OUTPUT)..."
	pandoc $(INPUT) -t revealjs -s -o $(OUTPUT) \
	  --css $(CSS_FILE) \
	  --slide-level=$(SLIDE_LEVEL) \
	  --template=custom-revealjs-template.html \
	  -V theme=$(THEME) \
	  -V revealjs-url=$(REVEAL_URL) \
	  -V transition=$(TRANSITION) \
	  --highlight-style=$(HIGHLIGHT_STYLE) \
	  --include-in-header=header.html \
	  --include-before-body=include-before.html \
	  --include-after-body=include-after.html \
	  --mathjax
	@echo "Build complete: $(OUTPUT)"

clean:
	@echo "Cleaning up generated files..."
	rm -f $(OUTPUT)
	@echo "Clean complete."
