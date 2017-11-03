#!/usr/bin/env python

import sys

# import sailfish
sys.path.append('../sailfish')
from sailfish.subdomain import Subdomain2D
from sailfish.node_type import NTHalfBBWall, NTEquilibriumVelocity, NTEquilibriumDensity, DynamicValue, NTFullBBWall
from sailfish.controller import LBSimulationController
from sailfish.lb_base import ForceObject
from sailfish.lb_single import LBFluidSim
from sailfish.sym import S

sys.path.append('../latnet/utils')
import binvox_rw as binvox_rw
import numpy as np
import glob

def rand_vel(max_vel=.10, min_vel=.09):
  vel = np.random.uniform(min_vel, max_vel)
  angle = np.random.uniform(-np.pi/2, np.pi/2)
  vel_x = vel * np.cos(angle)
  vel_y = vel * np.sin(angle)
  return (vel_x, vel_y)

def floodfill(image, x, y):
    edge = [(x, y)]
    image[x,y] = -1
    while edge:
        newedge = []
        for (x, y) in edge:
            for (s, t) in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if     ((0 <= s) and (s < image.shape[0])
                   and (0 <= t) and (t < image.shape[1])
                   and (image[s, t] == 0)):
                    image[s, t] = -1 
                    newedge.append((s, t))
        edge = newedge


class BoxSubdomain(Subdomain2D):
  bc = NTFullBBWall
  max_v = 0.1
  vel = rand_vel()

  def boundary_conditions(self, hx, hy):

    # set walls
    walls = (hx == -2) # set to all false
    y_wall = np.random.randint(0,2)
    if y_wall == 0:
      print("y wall")
      walls = (hy == 0) | (hy == self.gy - 1) | walls
    # x bottom
    #x_wall = np.random.randint(0,2) 
    #if x_wall == 1:
    #  walls = (hx == self.gx - 1) | walls
    self.set_node(walls, self.bc)

    self.set_node((hx == 0) & np.logical_not(walls),
                  NTEquilibriumVelocity(self.vel))

    # set open boundarys 
    self.set_node((hx == self.gx - 1) & np.logical_not(walls),
                  NTEquilibriumDensity(1))

    boundary = self.make_boundary(hx)
    self.set_node(boundary, self.bc)

    # save geometry (boundary, velocity, pressure)
    solid    = np.array(boundary | walls, dtype=np.float32) 
    solid    = np.expand_dims(solid, axis=-1)
    velocity = np.concatenate(2*[np.zeros_like(solid, dtype=np.float32)], axis=-1)
    velocity[:,0] = self.vel
    pressure = np.array((hx == self.gx - 1) & np.logical_not(walls), dtype=np.float32)
    pressure = np.expand_dims(pressure, axis=-1)
    geometry = np.concatenate([solid, velocity, pressure], axis=-1)
    np.save(self.config.checkpoint_file + "_geometry", geometry)

  def initial_conditions(self, sim, hx, hy):
    H = self.config.lat_ny
    sim.rho[:] = 1.0
    sim.vy[:] = self.vel[1]
    sim.vx[:] = self.vel[0]

  def make_boundary(self, hx):
    boundary = (hx == -2)
    all_vox_files = glob.glob('../../Flow-Sculpter/data/train/**/*.binvox')
    num_file_try = np.random.randint(2, 6)
    for i in xrange(num_file_try):
      file_ind = np.random.randint(0, len(all_vox_files))
      with open(all_vox_files[file_ind], 'rb') as f:
        model = binvox_rw.read_as_3d_array(f)
        model = model.data[:,:,model.dims[2]/2]
      model = np.array(model, dtype=np.int)
      model = np.pad(model, ((1,1),(1, 1)), 'constant', constant_values=0)
      floodfill(model, 0, 0)
      model = np.greater(model, -0.1)

      pos_x = np.random.randint(1, hx.shape[0]-model.shape[0]-1)
      pos_y = np.random.randint(1, hx.shape[1]-model.shape[1]-1)
      boundary[pos_x:pos_x+model.shape[0], pos_y:pos_y+model.shape[0]] = model | boundary[pos_x:pos_x+model.shape[0], pos_y:pos_y+model.shape[0]]

    return boundary

class BoxSimulation(LBFluidSim):
  subdomain = BoxSubdomain

  @classmethod
  def add_options(cls, group, defaults):
    group.add_argument('--sim_size',
            help='size of simulation to run ',
            type=int, default=512)

  @classmethod
  def update_defaults(cls, defaults):
    defaults.update({
      'max_iters': 50000,
      'output_format': 'npy',
      'periodic_y': True,
      'periodic_x': True,
      'checkpoint_file': './lkdsfj',
      'checkpoint_every': 200,
        })

  @classmethod
  def modify_config(cls, config):
    config.lat_nx = config.sim_size
    config.lat_ny = config.sim_size
    config.visc   = 0.1

  def __init__(self, *args, **kwargs):
    super(BoxSimulation, self).__init__(*args, **kwargs)

if __name__ == '__main__':
  sim = LBSimulationController(BoxSimulation)
  sim.run()
    

