#include <emscripten.h>
#include <math.h>

#define GRID_WIDTH 20
#define GRID_HEIGHT 20

// Electric charges: (x, y, q)
typedef struct {
  float x;
  float y;
  float q;
} Charge;

Charge charges[2];

// Output field: size = GRID_WIDTH * GRID_HEIGHT * 2 (x, y)
float field[GRID_WIDTH * GRID_HEIGHT * 2];

EMSCRIPTEN_KEEPALIVE
float* compute_field() {
  float k = 8.987551e9;

  for (int j = 0; j < GRID_HEIGHT; j++) {
    for (int i = 0; i < GRID_WIDTH; i++) {
      float px = (float)i / GRID_WIDTH;
      float py = (float)j / GRID_HEIGHT;
      float fx = 0.0f;
      float fy = 0.0f;

      for (int c = 0; c < 2; c++) {
        float dx = px - charges[c].x;
        float dy = py - charges[c].y;
        float r2 = dx * dx + dy * dy + 1e-4;  // Avoid division by zero
        float r = sqrtf(r2);
        float E = k * charges[c].q / r2;
        fx += E * dx / r;
        fy += E * dy / r;
      }

      int idx = (j * GRID_WIDTH + i) * 2;
      field[idx] = fx;
      field[idx + 1] = fy;
    }
  }

  return field;
}

EMSCRIPTEN_KEEPALIVE
void set_charges(float x1, float y1, float q1, float x2, float y2, float q2) {
  charges[0].x = x1;
  charges[0].y = y1;
  charges[0].q = q1;

  charges[1].x = x2;
  charges[1].y = y2;
  charges[1].q = q2;
}
