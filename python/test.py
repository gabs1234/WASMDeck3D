# coulomb.py
import numpy as np
from typing import Dict, Any, List

class Coulomb:
    def __init__(self, width: float, height: float, params: Dict[str, Any]):
        self.width = width
        self.height = height
        self.k = float(params.get('charge_strength', 1000.0))
        self.epsilon = 1e-6

        n_p = int(params.get('n_particles', 50))
        n_c = int(params.get('n_charges',    3))
        rng = np.random.default_rng()

        self.charges = rng.uniform([0,0], [width, height], size=(n_c,2)).astype(np.float32)
        signs = rng.choice([-1.0,1.0], size=n_c).astype(np.float32)
        self.charges = np.hstack([self.charges, signs[:,None]])

        self.particles  = rng.uniform([0,0], [width, height], size=(n_p,2)).astype(np.float32)
        self.particles = np.hstack([self.particles, np.zeros((n_p,1), dtype=np.float32)])
        self.velocities = np.zeros((n_p,2), dtype=np.float32)

    def get_charges(self) -> List[List[float]]:
        return [[float(x), float(y), float(q)] for x,y,q in self.charges]

    def update(self, dt: float) -> List[List[float]]:
        if self.particles.shape[0] == 0:
            return []

        p_xy = self.particles[:,:2][:,None,:]  # (n_p,1,2)
        c_xy = self.charges[:,:2][None,:,:]    # (1,n_c,2)
        c_q  = self.charges[:,2][None,:]       # (1,n_c)

        disp = p_xy - c_xy
        dist_sq = np.sum(disp**2, axis=2)
        dist = np.sqrt(np.maximum(dist_sq, self.epsilon))

        f_mag = self.k * c_q / np.maximum(dist_sq, self.epsilon)
        unit = disp / (dist[:,:,None] + self.epsilon)
        f_vec = f_mag[:,:,None] * unit
        total_f = np.sum(f_vec, axis=1)

        if dt > 0:
            self.velocities += total_f * dt
            self.particles[:,:2] += self.velocities * dt
            self.particles[:,0] = np.clip(self.particles[:,0], 0, self.width)
            self.particles[:,1] = np.clip(self.particles[:,1], 0, self.height)

        ke = 0.5 * np.sum(self.velocities**2, axis=1)
        self.particles[:,2] = ke.astype(np.float32)

        return [[float(x), float(y), float(k)] for x,y,k in self.particles.tolist()]