"""Efficient, original landscape geometry for the 50 m square ennichi scene.

Call build_landscape(api) after selecting the landscape collection in the
scene-building helpers. All dimensions are metres. No downloaded assets.
"""

import math
import random

import bpy
from mathutils import Vector


def build_landscape(api):
    def get(key):
        return api[key] if isinstance(api, dict) else getattr(api, key)

    cylinder = get("cylinder")
    materials = get("M")

    def material(key):
        return materials[key] if isinstance(materials, dict) else getattr(materials, key)

    def surface(name, color, roughness=.7, bump=.0, scale=8):
        mat = bpy.data.materials.get(name)
        if mat:
            return mat
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = roughness
        mat.diffuse_color = (*color, 1)
        if bump:
            tex = nodes.new("ShaderNodeTexNoise")
            tex.inputs["Scale"].default_value = scale
            tex.inputs["Detail"].default_value = 3
            bn = nodes.new("ShaderNodeBump")
            bn.inputs["Strength"].default_value = .28
            bn.inputs["Distance"].default_value = bump
            mat.node_tree.links.new(tex.outputs["Fac"], bn.inputs["Height"])
            mat.node_tree.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
        return mat

    soil = surface("Landscape_MoistGardenSoil", (.065, .041, .025), .98, .025, 34)
    bark = surface("Landscape_GreyBrownBark", (.115, .079, .052), .94, .018, 19)
    stone = surface("Landscape_WeatheredStone", (.28, .29, .25), .89, .02, 14)
    foliage = [surface("Landscape_Leaf_%02d" % i, color, .43)
               for i, color in enumerate([
                   (.042, .091, .016), (.064, .132, .023), (.087, .173, .031),
                   (.118, .208, .042), (.165, .244, .065)])]
    grass_mats = [surface("Landscape_Grass_%02d" % i, color, .68)
                  for i, color in enumerate([
                      (.082, .141, .028), (.135, .211, .047),
                      (.191, .252, .061), (.262, .264, .103)])]
    for leaf_mat in foliage:
        bsdf = leaf_mat.node_tree.nodes.get("Principled BSDF")
        if "Subsurface Weight" in bsdf.inputs:
            bsdf.inputs["Subsurface Weight"].default_value = .045

    # A real garden object establishes the same collection as the supplied
    # helper functions, avoiding assumptions about the active Blender context.
    first_soil = cylinder("Garden_NE_Soil", (17, 17, .027), 2.28, .045,
                          soil, vertices=64)
    collection = (first_soil.users_collection[0] if first_soil is not None
                  and first_soil.users_collection else bpy.context.collection)

    class MeshBuilder:
        def __init__(self):
            self.verts, self.faces, self.indices = [], [], []

        def face(self, verts, faces, mat=0):
            offset = len(self.verts)
            self.verts.extend(tuple(v) for v in verts)
            self.faces.extend(tuple(offset + n for n in f) for f in faces)
            self.indices.extend([mat] * len(faces))

        def box(self, center, dimensions, mat=0):
            x, y, z = center
            dx, dy, dz = [v * .5 for v in dimensions]
            v = [(x+a*dx, y+b*dy, z+c*dz)
                 for a, b, c in [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
                                (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
            self.face(v, [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5),
                          (2,3,7,6), (3,0,4,7)], mat)

        def tube(self, start, end, r0, r1=None, mat=0, sides=8):
            a, b = Vector(start), Vector(end)
            direction = b - a
            if direction.length < .00001:
                return
            direction.normalize()
            side = direction.cross(Vector((0, 0, 1)))
            if side.length < .01:
                side = direction.cross(Vector((0, 1, 0)))
            side.normalize()
            up = direction.cross(side).normalized()
            r1 = r0 if r1 is None else r1
            verts = []
            for p, radius in [(a, r0), (b, r1)]:
                for j in range(sides):
                    theta = j * math.tau / sides
                    verts.append(p + radius * (side * math.cos(theta) + up * math.sin(theta)))
            faces = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
            faces.extend((j, (j+1)%sides, (j+1)%sides+sides, j+sides)
                         for j in range(sides))
            self.face(verts, faces, mat)

        def ellipsoid(self, center, scale, mat=0, segments=9, rings=5):
            verts = []
            for i in range(rings + 1):
                phi = math.pi * i / rings
                for j in range(segments):
                    theta = math.tau * j / segments
                    verts.append((center[0] + scale[0] * math.sin(phi) * math.cos(theta),
                                  center[1] + scale[1] * math.sin(phi) * math.sin(theta),
                                  center[2] + scale[2] * math.cos(phi)))
            faces = []
            for i in range(rings):
                for j in range(segments):
                    k = i * segments + j
                    faces.append((k, i*segments+(j+1)%segments,
                                  (i+1)*segments+(j+1)%segments, k+segments))
            self.face(verts, faces, mat)

        def mesh(self, name, mats):
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(self.verts, [], self.faces)
            mesh.materials.clear()
            for mat in mats:
                mesh.materials.append(mat)
            mesh.update()
            for poly, index in zip(mesh.polygons, self.indices):
                poly.material_index = index
            return mesh

    def link(name, mesh, loc=(0, 0, 0), rotation=0, scale=1):
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler.z = rotation
        obj.scale = (scale, scale, scale)
        return obj

    # Four leaf/trunk variants share their mesh data across sixteen trees.
    # Each leaf has its own pointed outline and a raised midrib. The canopy is
    # made entirely of leaf surfaces, never spheres or visible cluster shells.
    tree_meshes = []
    for variant in range(4):
        rng = random.Random(871 + variant * 119)
        branches, leaves = MeshBuilder(), MeshBuilder()
        trunk_nodes = [Vector((0, 0, .03))]
        for j in range(1, 9):
            trunk_nodes.append(Vector((.065*j*math.sin(j*.62 + variant),
                                       .044*j*math.cos(j*.58 + variant), j*.89)))
        for j in range(8):
            branches.tube(trunk_nodes[j], trunk_nodes[j+1],
                          .31 - j*.030, .31 - (j+1)*.030, sides=11)
        for j in range(7):
            angle = j * math.tau / 7 + variant
            branches.tube((0, 0, .33), (.71*math.cos(angle), .71*math.sin(angle), .035),
                          .20, .025, sides=8)

        # Branch terminals provide spatially coherent leaf clusters with
        # visible gaps and irregular margins instead of a solid green mass.
        terminals = []
        for j in range(19):
            angle = j * 2.399963 + rng.uniform(-.21, .21)
            lower = j < 9
            origin = Vector((.07*math.sin(j), .06*math.cos(j),
                             rng.uniform(3.3, 4.8) if lower else rng.uniform(4.8, 6.6)))
            radius = rng.uniform(2.0, 2.65) if lower else rng.uniform(1.3, 2.3)
            crown_z = rng.uniform(5.5, 6.7) if lower else rng.uniform(7.1, 8.4)
            tip = Vector((radius*math.cos(angle), radius*math.sin(angle), crown_z))
            middle = origin.lerp(tip, .53)
            middle.z -= .22
            branches.tube(origin, middle, .135 if lower else .094, .062, sides=9)
            branches.tube(middle, tip, .064, .022, sides=8)
            for fork in range(3):
                a2 = angle + (fork-1)*.65 + rng.uniform(-.15, .15)
                end = tip + Vector((rng.uniform(.30, .76)*math.cos(a2),
                                    rng.uniform(.30, .76)*math.sin(a2),
                                    rng.uniform(.20, .72)))
                branches.tube(tip, end, .024, .008, sides=6)
                terminals.append(end)
        # A small crown around the trunk tip avoids a bald central apex.
        terminals.extend(Vector((rng.uniform(-.75, .75), rng.uniform(-.75, .75),
                                 rng.uniform(8.2, 8.8))) for _ in range(7))

        for terminal in terminals:
            for _ in range(105):
                phi, height = rng.uniform(0, math.tau), rng.uniform(-1, 1)
                radial = rng.random() ** (1/3)
                planar = math.sqrt(1-height*height)
                point = terminal + Vector((.71*radial*planar*math.cos(phi),
                                           .71*radial*planar*math.sin(phi),
                                           .71*radial*height))
                azimuth = rng.uniform(0, math.tau)
                tilt = rng.uniform(-.62, .62)
                along = Vector((math.cos(azimuth)*math.cos(tilt),
                                math.sin(azimuth)*math.cos(tilt), math.sin(tilt)))
                across = Vector((-math.sin(azimuth), math.cos(azimuth), rng.uniform(-.25, .25)))
                across.normalize()
                normal = along.cross(across).normalized()
                length, width = rng.uniform(.115, .205), rng.uniform(.052, .10)
                verts = [point,
                         point + along*length*.27 - across*width*.41,
                         point + along*length*.62 - across*width*.50,
                         point + along*length + normal*.014,
                         point + along*length*.62 + across*width*.50,
                         point + along*length*.27 + across*width*.41,
                         point + along*length*.50 + normal*.014]
                leaves.face(verts, [(0,1,6), (1,2,6), (2,3,6),
                                    (3,4,6), (4,5,6), (5,0,6)], rng.randrange(len(foliage)))
        branch_mesh = branches.mesh("Landscape_TreeBranchData_%02d" % variant, [bark])
        for poly in branch_mesh.polygons:
            poly.use_smooth = True
        leaf_mesh = leaves.mesh("Landscape_IndividualLeafData_%02d" % variant, foliage)
        tree_meshes.append((branch_mesh, leaf_mesh))

    rng = random.Random(9472)
    tree_locations = ([(x, -39.2) for x in (-24, -8, 8, 24)] +
                      [(x, 39.2) for x in (-24, -8, 8, 24)] +
                      [(-39.2, y) for y in (-24, -8, 8, 24)] +
                      [(39.2, y) for y in (-24, -8, 8, 24)])
    for i, (x, y) in enumerate(tree_locations):
        branch_mesh, leaf_mesh = tree_meshes[i % 4]
        scale = rng.uniform(.89, 1.19)
        rotation = rng.uniform(0, math.tau)
        location = (x + rng.uniform(-.45, .45), y + rng.uniform(-.45, .45), .025)
        link("OuterTree_%02d_TrunkBranches" % (i+1), branch_mesh, location, rotation, scale)
        link("OuterTree_%02d_IndividualLeaves" % (i+1), leaf_mesh, location, rotation, scale)

    # Four small inner corner gardens. Garden geometry ends before 19.5 m,
    # leaving over 2.5 m to the clear 22..28 m loop path.
    rng = random.Random(441)
    garden_stones, garden_grass = MeshBuilder(), MeshBuilder()
    for j in range(44):
        theta = j * math.tau / 44
        radius = 2.28 + rng.uniform(-.018, .018)
        garden_stones.ellipsoid((radius*math.cos(theta), radius*math.sin(theta), .075),
                                (rng.uniform(.115, .145), rng.uniform(.11, .14),
                                 rng.uniform(.065, .085)))
    for j in range(520):
        theta, radial = rng.uniform(0, math.tau), 2.10 * math.sqrt(rng.random())
        center = Vector((radial*math.cos(theta), radial*math.sin(theta), .051))
        for blade in range(rng.randint(4, 7)):
            direction = rng.uniform(0, math.tau)
            length = rng.uniform(.12, .34)
            lean = Vector((math.cos(direction), math.sin(direction), 0))
            width = Vector((-math.sin(direction), math.cos(direction), 0)) * rng.uniform(.004, .010)
            mid = center + lean*length*.15 + Vector((0, 0, length*.68))
            tip = center + lean*length*.55 + Vector((0, 0, length*.86))
            garden_grass.face([center-width, center+width, mid-width*.62, mid+width*.62, tip],
                              [(0,1,3,2), (2,3,4)], rng.randrange(len(grass_mats)))
    stone_mesh = garden_stones.mesh("Landscape_GardenBorderShared", [stone])
    for poly in stone_mesh.polygons:
        poly.use_smooth = True
    grass_mesh = garden_grass.mesh("Landscape_GardenGrassShared", grass_mats)
    for i, (x, y) in enumerate([(17,17), (-17,17), (-17,-17), (17,-17)]):
        if i:
            cylinder("Garden_%02d_Soil" % (i+1), (x, y, .027), 2.28, .045,
                     soil, vertices=64)
        link("Garden_%02d_StoneBorder" % (i+1), stone_mesh, (x,y,0), i*.71)
        link("Garden_%02d_GrassBlades" % (i+1), grass_mesh, (x,y,0), i*1.39)

    # Two separated runs per side leave the four cardinal entrances open.
    # Everything is beyond the back wall of the outer row of stalls.
    fence = MeshBuilder()
    for lo, hi in [(-30, -5), (5, 30)]:
        count = 10
        for j in range(count+1):
            x = lo + (hi-lo)*j/count
            fence.box((x, 0, .48), (.105, .105, .96))
            fence.box((x, 0, .965), (.127, .127, .035), 1)
        for j in range(count):
            mid = lo + (hi-lo)*(j+.5)/count
            for height in (.36, .76):
                fence.box((mid, 0, height), ((hi-lo)/count-.06, .065, .095))
    fence_mesh = fence.mesh("Landscape_OuterFenceShared", [material("wood"), material("darksteel")])
    for name, location, rotation in [
        ("South", (0,-33,0), 0), ("North", (0,33,0), 0),
        ("West", (-33,0,0), math.pi/2), ("East", (33,0,0), math.pi/2)]:
        obj = link("OuterFence_"+name, fence_mesh, location, rotation)
        bevel = obj.modifiers.new("Small worn edges", "BEVEL")
        bevel.width, bevel.segments = .007, 2

    # Park benches: six individual seat slats, three back slats, cast-metal
    # supports and visible fasteners. Local -Y faces the plaza center.
    bench = MeshBuilder()
    for j in range(6):
        bench.box((0, -.25 + j*.092, .46), (1.92, .078, .042))
    for z in (.64, .765, .89):
        bench.box((0, .282 + (z-.6)*.15, z), (1.92, .041, .095))
    for x in (-.73, .73):
        bench.box((x, 0, .403), (.072, .61, .075), 1)
        for y in (-.22, .23):
            bench.tube((x,y,.035), (x,y,.418), .027, mat=1, sides=10)
            bench.box((x,y,.034), (.16, .12, .028), 1)
        bench.tube((x,.24,.32), (x,.338,.94), .023, mat=1, sides=10)
        bench.tube((x,-.24,.16), (x,.24,.33), .019, mat=1, sides=8)
        for z in (.64, .765, .89):
            bench.tube((x,.250+(z-.6)*.15,z), (x,.263+(z-.6)*.15,z),
                       .0085, mat=2, sides=8)
    bench_mesh = bench.mesh("Landscape_BenchShared", [material("wood"), material("darksteel"), material("steel")])
    bench_positions = [(-10,-19,math.pi), (10,-19,math.pi),
                       (-10,19,0), (10,19,0),
                       (-19,-10,math.pi/2), (-19,10,math.pi/2),
                       (19,-10,-math.pi/2), (19,10,-math.pi/2)]
    for i, (x,y,angle) in enumerate(bench_positions):
        obj = link("PlazaBench_%02d" % (i+1), bench_mesh, (x,y,.015), angle)
        bevel = obj.modifiers.new("Rounded bench edges", "BEVEL")
        bevel.width, bevel.segments = .009, 2

    return {"trees": 16, "tree_mesh_variants": 4, "gardens": 4,
            "benches": 8, "fence_sides": 4,
            "clear_loop_inner_edge_m": 22, "clear_loop_outer_edge_m": 28,
            "landscape_collection": collection.name}
