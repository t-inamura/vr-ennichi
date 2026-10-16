"""Detailed, scale-correct festival food counters for the En-nichi scene.
All coordinates are booth-local; counter surface is z=0.96 m.
No external assets. Designed for Blender 4+ (also compatible with 3.6).
"""
import bpy
import math
import random
from mathutils import Vector


def build_food(kind, parent, api):
    rng = random.Random(sum((i + 1) * ord(c) for i, c in enumerate(kind)) + 2016)
    M = api['M']
    prefix = 'Food_' + kind + '_'
    serial = [0]

    def name(label):
        serial[0] += 1
        return prefix + label + '_' + str(serial[0])

    def material(label, color, roughness=.45, metallic=0., bump=.035, scale=100., transmission=0.):
        key = 'FoodMaterial_' + label
        found = bpy.data.materials.get(key)
        if found:
            return found
        m = bpy.data.materials.new(key)
        m.diffuse_color = (*color, 1.)
        m.use_nodes = True
        nt = m.node_tree
        p = nt.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1.)
        p.inputs['Roughness'].default_value = roughness
        p.inputs['Metallic'].default_value = metallic
        if 'Transmission Weight' in p.inputs:
            p.inputs['Transmission Weight'].default_value = transmission
        elif 'Transmission' in p.inputs:
            p.inputs['Transmission'].default_value = transmission
        if 'Subsurface Weight' in p.inputs:
            p.inputs['Subsurface Weight'].default_value = .04 if label in ['baked', 'flour', 'salmon'] else .0
        if bump:
            n = nt.nodes.new('ShaderNodeTexNoise')
            n.inputs['Scale'].default_value = scale
            n.inputs['Detail'].default_value = 3.
            b = nt.nodes.new('ShaderNodeBump')
            b.inputs['Strength'].default_value = bump
            b.inputs['Distance'].default_value = .025
            nt.links.new(n.outputs['Fac'], b.inputs['Height'])
            nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
        return m

    baked = material('baked', (.58,.24,.058), .57, bump=.24, scale=82.)
    golden = material('golden', (.87,.49,.12), .51, bump=.13, scale=98.)
    char = material('char', (.045,.016,.009), .74, bump=.18)
    mayo = material('mayonnaise', (.99,.9,.65), .3, bump=.0)
    sauce = material('brown_sauce', (.16,.041,.012), .2, bump=.018)
    candy = material('candy_red', (.65,.012,.018), .12, bump=.016, scale=20.)
    oil = material('fryer_oil', (.28,.135,.014), .13, bump=.008, transmission=.2)
    ice = material('crushed_ice', (.7,.93,1.), .18, bump=.18, scale=160., transmission=.35)
    leaf = M['leaf']
    metal = M['steel']
    floor_z = .965

    def cube(label, pos, dims, mat, bevel=.01):
        return api['cube'](name(label), pos, dims, mat, parent=parent, bevel=bevel)

    def ball(label, pos, scale, mat):
        return api['sphere'](name(label), pos, scale, mat, parent=parent)

    def cyl(label, pos, radius, depth, mat, vertices=24, rotation=None):
        return api['cylinder'](name(label), pos, radius, depth, mat, parent=parent, vertices=vertices, rotation=rotation)

    def rod(label, a, b, radius, mat):
        return api['rod'](name(label), a, b, radius, mat, parent=parent)

    def torus(label, pos, major, minor, mat, rotation=None):
        return api['torus'](name(label), pos, major, minor, mat, parent=parent, rotation=rotation)

    def lines(label, paths, radius, mat):
        if not paths:
            return None
        cu = bpy.data.curves.new(name(label), 'CURVE')
        cu.dimensions = '3D'
        cu.resolution_u = 2
        cu.bevel_depth = radius
        cu.bevel_resolution = 2
        for path in paths:
            sp = cu.splines.new('POLY')
            sp.points.add(len(path) - 1)
            for p, co in zip(sp.points, path):
                p.co = (*co, 1.)
        o = bpy.data.objects.new(cu.name, cu)
        parent.users_collection[0].objects.link(o)
        o.parent = parent
        cu.materials.append(mat)
        return o

    def mesh(label, vertices, faces, mat, smooth=False):
        me = bpy.data.meshes.new(name(label))
        me.from_pydata(vertices, [], faces)
        me.materials.append(mat)
        me.update()
        o = bpy.data.objects.new(me.name, me)
        parent.users_collection[0].objects.link(o)
        o.parent = parent
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        return o

    def ellipsoids(label, entries, mat, seg=16, rings=10, irregular=.0):
        """Merge many food pieces into one mesh to keep the scene light."""
        vv, ff = [], []
        for pos, scale in entries:
            start = len(vv)
            for j in range(rings + 1):
                t = math.pi * j / rings
                for i in range(seg):
                    a = 2 * math.pi * i / seg
                    noise = 1. + rng.uniform(-irregular, irregular)
                    vv.append((pos[0] + scale[0] * math.sin(t) * math.cos(a) * noise,
                               pos[1] + scale[1] * math.sin(t) * math.sin(a) * noise,
                               pos[2] + scale[2] * math.cos(t) * noise))
            for j in range(rings):
                for i in range(seg):
                    a = start + j * seg + i
                    b = start + j * seg + (i + 1) % seg
                    ff.append((a,b,b+seg,a+seg))
        return mesh(label, vv, ff, mat, True)

    def lathe(label, x, y, z, profile, mat, segments=40):
        vv, ff = [], []
        for radius, height in profile:
            for j in range(segments):
                a = j * 2. * math.pi / segments
                vv.append((x + radius*math.cos(a), y + radius*math.sin(a), z + height))
        for i in range(len(profile) - 1):
            for j in range(segments):
                a = i * segments + j
                b = i * segments + (j + 1) % segments
                ff.append((a,b,b+segments,a+segments))
        return mesh(label, vv, ff, mat, True)

    def bowl(x, y, z=floor_z, radius=.15, mat=None):
        mat = mat or M['white']
        lathe('bowl', x,y,z, [(0,0),(.62*radius,0),(.76*radius,.018),(radius,.1),
                              (radius+.008,.103),(radius+.007,.11),(radius-.008,.11),
                              (.74*radius,.025),(0,.025)], mat)
        return z + .07

    def tray(x,y,z=floor_z,w=.56,d=.37,mat=None):
        mat=mat or metal
        cube('tray_base',(x,y,z+.012),(w,d,.023),mat,.014)
        for xx in [x-w/2,x+w/2]:
            cube('tray_rim',(xx,y,z+.036),(.014,d,.055),mat,.009)
        for yy in [y-d/2,y+d/2]:
            cube('tray_rim',(x,yy,z+.036),(w,.014,.055),mat,.009)
        return z + .04

    def paperboat(x,y,z=floor_z,w=.23,d=.14):
        vv=[(x-w/2,y-d/2,z+.04),(x+w/2,y-d/2,z+.04),(x+w/2,y+d/2,z+.04),(x-w/2,y+d/2,z+.04),
            (x-w*.40,y-d*.37,z),(x+w*.4,y-d*.37,z),(x+w*.4,y+d*.37,z),(x-w*.4,y+d*.37,z)]
        mesh('paper_boat',vv,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],M['cream'])
        return z + .025

    def bottle(x,y,z,mat=M['red'],h=.22,r=.035):
        lathe('bottle', x,y,z, [(0,0),(r*.88,0),(r,.014),(r,h*.7),(r*.48,h*.81),
                              (r*.43,h*.95),(r*.46,h),(0,h)],mat,24)
        cyl('bottle_cap',(x,y,z+h+.008),r*.48,.016,M['white'])

    def squeeze(x,y,z=floor_z,mat=mayo):
        bottle(x,y,z,mat,h=.23,r=.04)
        cyl('squeeze_nozzle',(x,y,z+.256),.009,.042,M['white'])

    def grill(x=.05,y=.42,w=1.2,d=.58):
        cube('griddle_base',(x,y,1.045),(w,d,.18),metal,.025)
        cube('griddle_hotplate',(x,y,1.143),(w-.04,d-.04,.025),M['darksteel'],.012)
        cube('splashback',(x,y+d/2-.025,1.27),(w,.025,.24),metal)
        for xx in [x-w*.29,x+w*.29]:
            cyl('gas_knob',(xx,y-d/2-.017,1.02),.033,.022,M['black'],rotation=(math.pi/2,0,0))
        return 1.16

    def tongs(x,y,z=floor_z+.07):
        lines('steel_tongs',[[(x-.04,y-.09,z),(x,y+.10,z+.02),(x+.04,y-.09,z)]],.005,metal)

    def serving_tools():
        cyl('chopstick_cup',(1.43,-.67,1.035),.058,.14,M['bamboo'])
        for i in range(8):
            xx=1.43+rng.uniform(-.033,.033)
            yy=-.67+rng.uniform(-.033,.033)
            rod('chopstick',(xx,yy,1.04),(xx+rng.uniform(-.03,.03),yy,1.31+rng.uniform(-.018,.018)),.0027,M['bamboo'])
        cube('napkin_holder',(1.34,-1.0,1.005),(.21,.13,.07),M['wood'])
        cube('napkins',(1.34,-1.0,1.047),(.18,.10,.028),M['white'],.003)
        # Stacked supply cartons and insulated ingredient containers behind counter.
        cube('ingredient_box',(-1.25,.78,.30),(.53,.48,.56),M['cream'],.012)
        cube('ingredient_box_lid',(-1.25,.78,.59),(.56,.50,.04),M['white'],.007)

    def herbs_on(centers, z, count=28):
        entries=[]
        for x,y,rad in centers:
            for i in range(count):
                a=rng.random()*math.tau
                r=math.sqrt(rng.random())*rad
                entries.append(((x+r*math.cos(a),y+r*math.sin(a),z+rng.uniform(.0,.009)),(.007,.014,.0025)))
        ellipsoids('nori_and_scallions',entries,leaf,8,4)

    def drizzles(centers,z,mat=mayo,width=.005):
        paths=[]
        for x,y,r in centers:
            for i in range(4):
                yy=y-r*.65+i*r*.40
                paths.append([(x-r*.86 + j*r*1.72/20, yy + .015*math.sin(j*.8), z+.004*math.sin(j*.5)) for j in range(21)])
        lines('sauce_drizzle',paths,width,mat)

    def skewers(entries,z,orientation='y'):
        for x,y in entries:
            rod('bamboo_skewer',(x,y-.19,z),(x,y+.16,z),.0029,M['bamboo'])

    serving_tools()

    if kind == 'cotton_candy':
        # Spun-sugar machine with rolled steel basin, spindle and switch panel.
        cube('candy_machine',(-.55,.33,1.12),(.69,.64,.31),M['pink'],.05)
        lathe('spinning_bowl',-.55,.33,1.265,[(0,0),(.22,0),(.28,.018),(.40,.17),(.41,.18),(.403,.193),(.393,.185),(.265,.035),(0,.026)],metal)
        cyl('spinner',(-.55,.33,1.33),.072,.13,M['darksteel'])
        cyl('sugar_spindle',(-.55,.33,1.404),.046,.018,metal)
        for i in range(2):
            cube('machine_switch',(-.72+i*.18,-.001,1.13),(.07,.019,.045),M['red'] if i==0 else M['black'])
        fluffywhite=material('sugar_floss_white',(.98,.91,.83),.91,bump=.42,scale=410.)
        fluffypink=material('sugar_floss_pink',(.95,.50,.65),.94,bump=.42,scale=410.)
        cube('cotton_candy_rack',(.64,-.80,1.015),(.85,.28,.08),M['wood'])
        for i in range(6):
            x=.26+i*.15
            y=-.82+(i%2)*.06
            z=1.48+(i%2)*.14
            rod('candy_stick',(x,y,1.0),(x,y,z+.05),.004,M['bamboo'])
            blobs=[]
            for j in range(20):
                a=rng.random()*math.tau
                t=rng.uniform(-.12,.15)
                rad=.067*math.sqrt(max(0.,1.-(t/.19)**2))
                blobs.append(((x+rad*.57*math.cos(a),y+rad*.57*math.sin(a),z+t),(.070,.063,.085)))
            ellipsoids('spun_sugar',blobs,fluffypink if i%3 else fluffywhite,16,10,.06)
        bottle(-1.04,-.8,floor_z,M['pink'],h=.2,r=.071)
        bottle(-1.26,-.8,floor_z,M['white'],h=.2,r=.071)

    elif kind in ('apple_candy','strawberry_candy','candied_grapes'):
        glazedgreen=material('candy_grape_green',(.26,.54,.054),.12,bump=.018)
        cube('candy_display_plinth',(0,-.82,1.005),(2.15,.52,.075),M['wood'])
        rodpaths=[]
        for row in range(2):
            for i in range(8):
                x=-.92+i*.26
                y=-.93+row*.23
                if kind == 'apple_candy':
                    z=1.15
                    ball('glazed_apple',(x,y,z),(.092,.086,.091),candy)
                    rod('apple_stick',(x,y,1.16),(x,y,1.48),.0032,M['bamboo'])
                    ball('apple_indent',(x,y,1.237),(.023,.018,.007),sauce)
                else:
                    rod('fruit_skewer',(x,y,1.03),(x,y,1.53),.0028,M['bamboo'])
                    entries=[]
                    for j in range(3):
                        if kind=='strawberry_candy':
                            entries.append(((x,y,1.11+j*.09),(.047,.042,.058)))
                        else:
                            entries.append(((x,y,1.10+j*.074),(.043,.039,.041)))
                    ellipsoids('glazed_fruit',entries,candy if kind=='strawberry_candy' else glazedgreen,16,12,.035)
                    if kind=='strawberry_candy':
                        herbs_on([(x,y,.039)],1.15,count=6)
        tray(-.69,.40,z=1.0,w=.64,d=.43)
        cyl('sugar_syrup_pot',(.44,.43,1.13),.23,.31,metal)
        cyl('red_syrup',(.44,.43,1.288),.211,.014,candy)
        torus('pot_handle',(.68,.43,1.20),.069,.01,metal,rotation=(math.pi/2,0,0))
        rod('syrup_spatula',(.48,.43,1.25),(.80,.47,1.61),.009,M['wood'])

    elif kind=='yakisoba':
        zz=grill(w=1.47,d=.72)
        # Hundreds of fine, curled individual noodles on the hotplate.
        paths=[]
        for i in range(270):
            cx=rng.uniform(-.49,.5); cy=rng.uniform(.17,.62)
            length=rng.uniform(.16,.44); angle=rng.random()*math.tau
            path=[]
            for j in range(20):
                t=(j/19-.5)*length
                wiggle=.020*math.sin(j*.68+i)
                path.append((cx+t*math.cos(angle)-wiggle*math.sin(angle),cy+t*math.sin(angle)+wiggle*math.cos(angle),zz+.015+rng.random()*.045))
            paths.append(path)
        lines('tangled_yakisoba_noodles',paths,.0042,M['noodle'])
        herbs_on([(0,.4,.48)],zz+.064,90)
        veg=[]
        for i in range(60):
            veg.append(((rng.uniform(-.55,.55),rng.uniform(.14,.66),zz+.045),(.024,.042,.008)))
        ellipsoids('cabbage',veg,material('cabbage',(.57,.65,.23),.54,bump=.04),10,6)
        for i in range(4):
            x=-.81+i*.48; y=-.84
            bz=paperboat(x,y,w=.38,d=.21)
            pp=[]
            for j in range(40):
                xx=x+rng.uniform(-.14,.14); yy=y+rng.uniform(-.065,.065)
                pp.append([(xx+.06*math.sin(k*.6+j),yy+.032*math.cos(k*.65),bz+.027+j*.0007) for k in range(14)])
            lines('served_yakisoba',pp,.0038,M['noodle'])
            herbs_on([(x,y,.10)],bz+.059,18)
        squeeze(1.05,.43,mat=sauce)
        cube('spatula_blade',(-.91,.26,1.14),(.13,.19,.009),metal,.002)
        rod('spatula_handle',(-.91,.26,1.15),(-1.04,-.01,1.25),.016,M['wood'])

    elif kind=='takoyaki':
        zz=grill(w=1.37,d=.63)
        centers=[]
        for row in range(4):
            for col in range(9):
                x=-.54+col*.137; y=.20+row*.132
                cyl('takoyaki_well',(x,y,zz+.003),.058,.007,M['black'],vertices=16)
                centers.append(((x,y,zz+.027),(.052,.052,.047)))
        ellipsoids('browning_takoyaki',centers,baked,16,10,.025)
        for k in range(4):
            x=-.83+k*.48; y=-.87; z=paperboat(x,y,w=.39,d=.20)
            pp=[((x+(i%3-1)*.096,y+(i//3-.5)*.091,z+.036),(.049,.047,.044)) for i in range(6)]
            ellipsoids('takoyaki_portion',pp,golden,16,10,.018)
            drizzles([(x,y,.13)],z+.078,sauce,.006)
            drizzles([(x,y,.12)],z+.083,mayo,.003)
            herbs_on([(x,y,.13)],z+.091,25)
        squeeze(1.04,.37)
        squeeze(1.22,.37,mat=sauce)
        rod('takoyaki_pick',(-.84,.30,1.14),(-.95,-.03,1.19),.003,metal)

    elif kind=='kakigori':
        # Cast-metal shaved ice machine, vertical press and shaving bowl.
        cube('ice_machine_foot',(-.65,.36,1.02),(.52,.48,.10),M['blue'],.035)
        for x in [-.88,-.42]:
            rod('ice_machine_column',(x,.42,1.06),(x,.42,1.84),.024,M['blue'])
        cube('ice_machine_top',(-.65,.42,1.84),(.61,.31,.09),M['blue'],.025)
        cyl('ice_pressure_screw',(-.65,.39,1.67),.018,.32,metal)
        cyl('press_disk',(-.65,.39,1.48),.14,.03,metal)
        cyl('ice_block',(-.65,.39,1.40),.14,.12,ice)
        lathe('shaver_cup',-.65,.39,1.25,[(.10,0),(.2,.06),(.2,.12),(.18,.12),(.08,.015)],metal)
        torus('ice_crank',(-.65,.42,1.94),.15,.012,metal)
        for i,ma in enumerate([candy,M['blue'],M['yellow'],M['green']]):
            bottle(.26+i*.23,.36,1.0,ma,h=.33,r=.071)
        for i in range(5):
            x=-1.+i*.44;y=-.86
            z=bowl(x,y,radius=.14)
            entries=[]
            for j in range(45):
                a=rng.random()*math.tau; rr=.12*math.sqrt(rng.random()); h=.10*(1.-rr/.14)
                entries.append(((x+rr*math.cos(a),y+rr*math.sin(a),z+h),(.027,.026,.021)))
            ellipsoids('shaved_ice',entries,ice,10,6,.14)
            ball('syrup_on_ice',(x,y,z+.079),(.087,.085,.026),[candy,M['blue'],M['yellow'],M['green'],candy][i])
            rod('ice_spoon',(x+.08,y,z),(x+.15,y+.04,z+.25),.0035,M['pink'])

    elif kind=='choco_banana':
        cube('banana_rack',(0,-.8,1.005),(2.10,.48,.075),M['wood'])
        for row in range(2):
            for i in range(8):
                x=-.90+i*.25; y=-.94+row*.24
                rod('banana_stick',(x,y,1.01),(x,y,1.36),.0033,M['bamboo'])
                p=[(x+.028*math.sin(j/14*math.pi),y,1.28+j*.014) for j in range(15)]
                lines('chocolate_banana',[p],.030,M['chocolate'] if i%3 else M['pink'])
                sprinkles=[]
                for j in range(13):
                    zz=1.31+rng.random()*.16
                    xx=x+rng.uniform(-.019,.03)
                    sprinkles.append([(xx,y-.029,zz),(xx+.006,y-.030,zz+.008)])
                lines('banana_sprinkles',sprinkles,.0017,[M['white'],M['yellow'],M['blue']][i%3])
        cyl('melting_pot',(-.55,.41,1.16),.23,.36,metal)
        cyl('melted_chocolate',(-.55,.41,1.343),.213,.009,M['chocolate'])
        tray(.48,.42,z=1.0,w=.71,d=.44)
        ellipsoids('bananas_in_tray',[((.25+i*.09,.42,1.085),(.036,.16,.036)) for i in range(6)],M['yellow'],16,8)

    elif kind=='taiyaki':
        zz=grill(w=1.26,d=.62)
        def fish(x,y,z,ma):
            ball('taiyaki_body',(x,y,z),(.10,.049,.033),ma)
            mesh('taiyaki_tail',[(x-.075,y,z+.025),(x-.15,y-.055,z+.013),(x-.15,y+.055,z+.013),
                                 (x-.075,y,z-.021),(x-.15,y-.055,z-.013),(x-.15,y+.055,z-.013)],[(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)],ma)
            ball('taiyaki_eye',(x+.063,y-.017,z+.031),(.006,.006,.0025),baked)
            pp=[]
            for i in range(5):
                xx=x-.052+i*.024
                pp.append([(xx-.017,y-.031,z+.022),(xx,y,z+.037),(xx+.017,y+.031,z+.022)])
            lines('taiyaki_scale_engraving',pp,.0016,baked)
        for i in range(8):
            fish(-.44+(i%4)*.29,.23+(i//4)*.22,zz+.031,baked)
        tray(-.08,-.82,w=1.80,d=.43)
        for i in range(12):
            fish(-.78+(i%6)*.29,-.94+(i//6)*.22,1.045,golden)
        tongs(1.0,-.81)

    elif kind in ('yakitori','ikayaki','corn','frankfurt','dango','cucumber'):
        zz=grill(w=1.36,d=.67) if kind not in ('dango','cucumber') else 1.04
        tray(-.1,-.86,w=2.04,d=.42)
        skentries=[]
        for row in range(2):
            for i in range(8):
                x=-.92+i*.235; y=-.98+row*.23
                skentries.append((x,y))
                rod('food_skewer',(x,y-.12,1.055),(x,y+.17,1.055),.0028,M['bamboo'])
                if kind=='yakitori':
                    ellipsoids('chicken_skewer',[((x,y+j*.052,1.084),(.030,.029,.030)) for j in [-1,0,1,2]],baked,12,8,.12)
                    for j in [-1,1]:
                        cube('negi_segment',(x,y+j*.046,1.087),(.047,.021,.038),M['cream'],.008)
                elif kind=='dango':
                    for j in range(3):
                        ball('rice_dumpling',(x,y-.057+j*.057,1.085),(.031,.031,.031),[M['pink'],M['white'],M['green']][j])
                elif kind=='frankfurt':
                    ball('grilled_frankfurter',(x,y+.014,1.085),(.033,.116,.032),material('sausage',(.46,.105,.036),.32,bump=.11))
                    lines('mustard_zigzag',[[(x+.019*math.sin(j*1.2),y-.076+j*.009,1.116) for j in range(20)]],.0026,M['yellow'])
                elif kind=='cucumber':
                    ball('cucumber_pickle',(x,y+.015,1.09),(.025,.133,.026),material('cucumber_skin',(.055,.17,.013),.38,bump=.19,scale=85.))
                    lines('cucumber_ridge',[[(x+.016,y-.094+j*.015,1.108) for j in range(15)]],.0018,leaf)
                elif kind=='corn':
                    ball('corn_cob',(x,y+.014,1.09),(.042,.112,.043),M['yellow'])
                    kernels=[]
                    for j in range(13):
                        for k in range(11):
                            a=k*math.tau/11
                            kernels.append(((x+.043*math.cos(a),y-.085+j*.016,1.092+.043*math.sin(a)),(.010,.010,.009)))
                    ellipsoids('individual_corn_kernels',kernels,golden,8,6,.035)
                else:
                    ball('whole_grilled_squid',(x,y+.025,1.085),(.052,.100,.034),material('squid_glaze',(.58,.26,.14),.28,bump=.08))
                    pp=[]
                    for j in range(5):
                        yy=y-.03+j*.028
                        pp.append([(x-.043,yy,1.095),(x,yy,1.123),(x+.043,yy,1.095)])
                    lines('squid_scored_grill_marks',pp,.0025,sauce)
                    pp=[]
                    for j in range(5):
                        pp.append([(x+(j-2)*.013,y-.075,1.071),(x+(j-2)*.019,y-.12,1.069),(x+(j-2)*.021+.012*math.sin(j),y-.16,1.070)])
                    lines('squid_tentacles',pp,.0065,baked)
        if kind not in ('dango','cucumber'):
            grillbars=[]
            for i in range(20):
                xx=-.56+i*.064
                grillbars.append([(xx,.13,zz+.013),(xx,.68,zz+.013)])
            lines('charcoal_grill_bars',grillbars,.004,metal)
            ellipsoids('charcoal', [((rng.uniform(-.48,.49),rng.uniform(.20,.59),zz-.005),(.07,.045,.018)) for _ in range(20)],char,10,6,.13)
        else:
            lathe('seasoning_vat',.35,.38,1.0,[(0,0),(.21,0),(.25,.27),(.235,.27),(.20,.025),(0,.025)],metal)
            cyl('seasoning_liquid',(.35,.38,1.23),.232,.01,sauce if kind=='dango' else M['water'])
        squeeze(1.13,.4,mat=sauce)
        tongs(-1.19,-.79)

    elif kind=='okonomiyaki':
        zz=grill(w=1.54,d=.74)
        centers=[(-.39,.28,.19),(.08,.31,.19),(.51,.43,.18)]
        for x,y,r in centers:
            cyl('okonomiyaki_pancake',(x,y,zz+.024),r,.047,golden,vertices=40)
            cyl('okonomiyaki_glaze',(x,y,zz+.050),r*.92,.009,sauce,vertices=40)
        drizzles(centers,zz+.060,mayo,.005)
        herbs_on(centers,zz+.067,40)
        for i in range(3):
            x=-.82+i*.63; y=-.86
            z=paperboat(x,y,w=.53,d=.30)
            cyl('served_okonomiyaki',(x,y,z+.023),.145,.041,baked,vertices=32)
            cyl('served_sauce',(x,y,z+.047),.133,.006,sauce,vertices=32)
            drizzles([(x,y,.12)],z+.053,mayo,.004)
            herbs_on([(x,y,.12)],z+.061,30)
        squeeze(1.17,.50)
        cube('turner_blade',(-1.11,.20,1.15),(.13,.22,.01),metal)
        rod('turner_handle',(-1.11,.14,1.16),(-1.09,-.06,1.24),.015,M['wood'])

    elif kind in ('karaage','potato'):
        cube('deep_fryer',(-.21,.39,1.12),(1.05,.67,.30),metal,.03)
        cube('fryer_well',(-.21,.37,1.279),(.94,.52,.025),M['darksteel'])
        cube('hot_oil',(-.21,.37,1.293),(.90,.47,.01),oil)
        for x in [-.47,.03]:
            paths=[]
            for i in range(9):
                xx=x-.20+i*.05
                paths.append([(xx,.16,1.31),(xx,.61,1.31)])
            for i in range(9):
                yy=.16+i*.055
                paths.append([(x-.20,yy,1.31),(x+.20,yy,1.31)])
            lines('wire_frying_basket',paths,.0016,metal)
            rod('basket_handle',(x,.16,1.31),(x,-.14,1.45),.010,metal)
            rod('basket_grip',(x,-.14,1.45),(x,-.31,1.45),.021,M['black'])
        tray(-.04,-.82,w=2.1,d=.47)
        if kind=='karaage':
            entries=[]
            for i in range(57):
                entries.append(((rng.uniform(-.97,.90),rng.uniform(-1.0,-.64),1.052+rng.uniform(0,.063)),(.048,.041,.036)))
            ellipsoids('crispy_fried_chicken',entries,baked,14,10,.18)
        else:
            paths=[]
            for i in range(160):
                x=rng.uniform(-.91,.83);y=rng.uniform(-.99,-.66);a=rng.random()*math.tau;l=rng.uniform(.07,.14);z=1.062+rng.random()*.046
                paths.append([(x,y,z),(x+l*math.cos(a),y+l*math.sin(a),z+.016)])
            lines('french_fries',paths,.008,golden)
        for i in range(3):
            bowl(.80+i*.15,.37,z=1.0,radius=.069)
        squeeze(-1.12,.32,mat=candy)
        tongs(1.17,-.78)

    elif kind=='crepe':
        cube('crepe_griddle_base',(-.35,.38,1.075),(.78,.65,.19),metal,.03)
        cyl('round_crepe_griddle',(-.35,.38,1.186),.29,.028,M['darksteel'],vertices=64)
        cyl('cooking_crepe',(-.35,.38,1.202),.264,.005,M['cream'],vertices=64)
        rod('crepe_spreader',(-.60,.45,1.216),(-.12,.45,1.216),.011,M['wood'])
        rod('spreader_handle',(-.36,.45,1.22),(-.36,.07,1.24),.009,M['wood'])
        cube('crepe_rack',(0,-.84,1.016),(2.08,.33,.07),M['wood'])
        for i in range(7):
            x=-.91+i*.29;y=-.86
            # Folded golden pancake in a paper cone, with visible cream and fruit.
            lathe('paper_cone',x,y,1.03,[(.019,0),(.070,.20),(.061,.20),(.014,.012)],M['white'],32)
            lathe('folded_crepe',x,y,1.05,[(.016,0),(.081,.24),(.079,.244),(.060,.19),(.014,.016)],golden,32)
            ellipsoids('whipped_cream',[((x+.034*math.cos(j*2.1),y+.032*math.sin(j*2.1),1.285+j*.004),(.032,.029,.025)) for j in range(5)],M['cream'],16,10)
            ball('crepe_strawberry',(x-.025,y-.012,1.328),(.026,.024,.034),candy)
            ball('crepe_banana_slice',(x+.036,y+.019,1.319),(.028,.023,.008),M['yellow'])
        squeeze(.39,.30,mat=M['chocolate'])
        squeeze(.59,.31)
        bowl(.89,.4,z=1.0,radius=.15)

    elif kind=='baby_castella':
        zz=grill(w=1.29,d=.58)
        for row in range(4):
            for col in range(9):
                cyl('castella_mold',(-.51+col*.127,.18+row*.112,zz+.005),.045,.009,M['black'],vertices=16)
        tray(-.07,-.84,w=1.96,d=.45)
        pp=[]
        for i in range(70):
            pp.append(((rng.uniform(-.91,.86),rng.uniform(-.99,-.66),1.065+rng.uniform(0,.057)),(.038,.029,.034)))
        ellipsoids('baby_castella_cakes',pp,golden,12,10,.10)
        cyl('batter_pitcher',(.99,.35,1.17),.13,.34,metal)
        torus('pitcher_handle',(1.14,.35,1.18),.086,.010,metal,rotation=(math.pi/2,0,0))
        tongs(1.12,-.83)

    elif kind=='rice_cracker':
        zz=grill(w=1.2,d=.6)
        for i in range(6):
            x=-.43+(i%3)*.42;y=.22+(i//3)*.28
            cyl('grilling_senbei',(x,y,zz+.013),.111,.022,golden,vertices=40)
            cube('senbei_nori',(x,y,zz+.026),(.14,.055,.005),leaf,.005)
        for i in range(5):
            x=-.91+i*.40;y=-.85
            paperboat(x,y,w=.33,d=.26)
            for j in range(4):
                cyl('stacked_senbei',(x,y,1.017+j*.020),.111,.018,baked if j%2 else golden,vertices=32)
            cube('senbei_nori',(x,y,1.09),(.14,.05,.006),leaf,.002)
        squeeze(1.01,.40,mat=sauce)
        tongs(1.16,-.82)

    elif kind in ('lemonade','ramune','tea','beer'):
        if kind in ('ramune','tea'):
            cube('drink_ice_chest',(-.05,-.83,1.095),(2.04,.48,.25),M['blue'],.035)
            cube('ice_chest_interior',(-.05,-.83,1.231),(1.92,.39,.025),M['white'],.018)
            entries=[]
            for i in range(65):
                entries.append(((rng.uniform(-.94,.84),rng.uniform(-.99,-.66),1.25+rng.uniform(-.01,.02)),(.026,.031,.020)))
            ellipsoids('ice_cubes',entries,ice,8,6,.16)
            for row in range(2):
                for i in range(10):
                    x=-.91+i*.192;y=-.96+row*.24
                    if kind=='ramune':
                        green_glass=material('ramune_glass',(.18,.53,.47),.16,transmission=.65)
                        lathe('ramune_bottle',x,y,1.18,[(0,0),(.025,0),(.029,.03),(.026,.12),(.033,.16),(.020,.19),(.017,.23),(.025,.24),(.022,.26),(0,.26)],green_glass,20)
                        cyl('ramune_label',(x,y,1.258),.029,.052,M['white'],vertices=20)
                        cyl('ramune_cap',(x,y,1.444),.025,.018,M['blue'])
                    else:
                        bottle(x,y,1.16,material('bottled_tea',(.17,.27,.039),.26),h=.23,r=.033)
                        cyl('tea_label',(x,y,1.282),.034,.064,M['cream'],vertices=20)
            cube('spare_drink_crate',(.28,.74,.30),(.66,.54,.57),M['blue'],.02)
        elif kind=='lemonade':
            for i in range(2):
                x=-.62+i*.86;y=.38
                cube('dispenser_stand',(x,y,1.10),(.53,.47,.20),M['wood'])
                lathe('glass_drink_dispenser',x,y,1.2,[(0,0),(.22,0),(.24,.07),(.24,.58),(.21,.62),(.20,.62),(.23,.58),(.23,.025),(0,.025)],M['glass'])
                cyl('lemon_drink',(x,y,1.46),.223,.46,material('lemon_drink',(.93,.64,.10),.17,transmission=.35))
                cyl('dispenser_lid',(x,y,1.83),.236,.03,metal)
                rod('drink_tap',(x,y-.23,1.29),(x,y-.33,1.29),.016,metal)
                rod('tap_spout',(x,y-.33,1.29),(x,y-.33,1.24),.011,metal)
                for j in range(4):
                    cyl('floating_lemon_slice',(x+rng.uniform(-.11,.11),y+rng.uniform(-.13,.11),1.25+j*.10),.072,.015,M['yellow'],vertices=32)
            for i in range(7):
                x=-.96+i*.31;y=-.86
                lathe('lemonade_cup',x,y,floor_z,[(0,0),(.045,0),(.060,.15),(.057,.15),(.042,.008),(0,.008)],M['glass'],24)
                cyl('cup_lemonade',(x,y,1.028),.05,.109,M['yellow'])
                rod('paper_straw',(x+.02,y,1.02),(x+.033,y,1.24),.0032,M['white'])
                torus('lemon_rind',(x-.018,y,1.125),.043,.009,M['yellow'],rotation=(math.pi/3,0,0))
        else:
            cube('beer_chiller',(-.37,.38,1.15),(.69,.61,.39),metal,.04)
            rod('beer_tower',(-.35,.38,1.35),(-.35,.38,1.88),.051,metal)
            rod('beer_tap',(-.35,.38,1.81),(-.35,.13,1.81),.026,metal)
            rod('beer_spout',(-.35,.13,1.81),(-.35,.13,1.73),.011,metal)
            rod('tap_lever',(-.35,.16,1.85),(-.35,.16,2.01),.012,M['black'])
            for i in range(7):
                x=-.97+i*.31;y=-.86
                lathe('beer_cup',x,y,floor_z,[(0,0),(.050,0),(.065,.20),(.061,.20),(.046,.008),(0,.008)],M['glass'],32)
                cyl('golden_beer',(x,y,1.052),.057,.166,material('golden_beer',(.8,.37,.012),.16,transmission=.3))
                cyl('beer_foam',(x,y,1.151),.061,.035,M['cream'],vertices=32)
                ellipsoids('foam_bubbles',[((x+rng.uniform(-.040,.040),y+rng.uniform(-.04,.04),1.172),(.010,.010,.006)) for j in range(12)],M['white'],8,6)
            cyl('beer_keg',(.80,.67,.42),.25,.77,metal,vertices=40)
            for z in [.08,.16,.66,.77]:
                torus('keg_ridge',(.80,.67,z),.253,.012,metal)

    elif kind=='yakionigiri':
        zz=grill(w=1.33,d=.60)
        def riceball(x,y,z):
            vv=[(x-.065,y-.043,z),(x+.065,y-.043,z),(x,y-.043,z+.13),(x-.065,y+.043,z),(x+.065,y+.043,z),(x,y+.043,z+.13)]
            ob=mesh('grilled_onigiri',vv,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],golden)
            bevel=ob.modifiers.new('soft rice corners','BEVEL');bevel.width=.012;bevel.segments=3
            cube('onigiri_nori',(x,y-.046,z+.04),(.068,.004,.058),leaf,.008)
            rice=[]
            for i in range(18):
                zz2=rng.uniform(.012,.10);xx=rng.uniform(-1,1)*(.060-.42*zz2)
                rice.append(((x+xx,y-.046,z+zz2),(.004,.0025,.0025)))
            ellipsoids('rice_grains',rice,M['cream'],8,4)
        for i in range(8):riceball(-.47+(i%4)*.28,.22+(i//4)*.25,zz+.01)
        tray(-.07,-.85,w=1.95,d=.41)
        for i in range(10):riceball(-.85+(i%5)*.37,-.94+(i//5)*.20,1.005)
        squeeze(1.1,.38,mat=sauce)

    elif kind=='sweet_potato':
        cube('roasting_oven',(-.24,.52,.76),(1.30,.68,1.45),M['darksteel'],.055)
        cube('oven_door',(-.24,.158,.84),(1.12,.045,.66),metal,.026)
        cube('oven_window',(-.24,.128,.86),(.88,.018,.39),M['black'],.018)
        rod('oven_handle',(-.65,.09,1.19),(.19,.09,1.19),.018,metal)
        tray(-.03,-.85,w=2.10,d=.48)
        purple=material('roast_sweet_potato_skin',(.23,.057,.051),.66,bump=.36,scale=130.)
        for i in range(11):
            x=-.91+(i%6)*.33;y=-.97+(i//6)*.23
            ball('roast_potato',(x,y,1.05),(.058,.12,.046),purple)
            if i%3==0:
                ball('exposed_sweet_potato',(x,y-.015,1.085),(.041,.075,.022),M['yellow'])
        tongs(1.2,-.87)

    elif kind=='soft_serve':
        cube('icecream_machine',(-.39,.49,1.43),(.78,.65,.95),metal,.045)
        cube('machine_front',(-.39,.147,1.55),(.66,.034,.59),M['white'],.024)
        cube('machine_display',(-.39,.124,1.69),(.21,.018,.10),M['black'],.015)
        for x in [-.57,-.22]:
            cyl('serve_nozzle',(x,.10,1.27),.025,.10,M['black'])
            rod('serve_lever',(x,.11,1.48),(x,-.02,1.36),.016,M['black'])
        cube('cone_rack',(.06,-.85,1.006),(2.04,.35,.075),M['wood'])
        for i in range(7):
            x=-.87+i*.29;y=-.85
            lathe('waffle_cone',x,y,1.03,[(.008,0),(.058,.18),(.052,.18),(.004,.014)],golden,32)
            paths=[]
            for k in range(6):
                a=k*math.tau/6
                paths.append([(x+(.008+j*.003)*math.cos(a+j*.24),y+(.008+j*.003)*math.sin(a+j*.24),1.03+j*.01) for j in range(17)])
            lines('cone_waffle_ridges',paths,.0015,baked)
            spiral=[]
            for j in range(180):
                t=j/179;r=.058*(1.-t)*.97+.003;a=t*math.tau*4.6
                spiral.append((x+r*math.cos(a),y+r*math.sin(a),1.21+t*.20))
            lines('softserve_swirl',[spiral],.017,M['cream'] if i%3 else M['chocolate'])

    elif kind=='fruit_cup':
        tray(-.1,-.85,w=2.09,d=.46)
        for row in range(2):
            for i in range(7):
                x=-.91+i*.28;y=-.97+row*.25
                lathe('fruit_cup',x,y,1.002,[(0,0),(.049,0),(.063,.12),(.059,.12),(.045,.007),(0,.007)],M['glass'],24)
                for j,ma in enumerate([M['red'],M['yellow'],M['orange'],M['green']]):
                    ball('cut_fruit',(x+.026*math.cos(j*1.7),y+.026*math.sin(j*1.7),1.066+j*.012),(.028,.026,.024),ma)
                rod('fruit_fork',(x+.01,y,1.06),(x+.029,y+.02,1.25),.0027,M['bamboo'])
        cube('cutting_board',(-.45,.34,1.017),(.77,.47,.036),M['white'])
        ball('watermelon',(.65,.51,1.23),(.24,.23,.22),M['green'])
        ball('cut_melon',(-.53,.39,1.135),(.18,.16,.105),M['orange'])
        cube('knife_blade',(-.01,.29,1.04),(.24,.041,.007),metal,.003)
        cube('knife_handle',(.17,.29,1.045),(.13,.033,.019),M['black'])

    elif kind=='grilled_scallop':
        zz=grill(w=1.37,d=.69)
        def scallop(x,y,z):
            vv=[];ff=[];rows=7;segs=24
            for i in range(rows):
                rr=i/(rows-1)*.096
                for j in range(segs+1):
                    a=math.pi*.06+j/segs*math.pi*.88
                    r=rr*(1.+.033*math.cos(j*math.pi))
                    vv.append((x+r*math.cos(a),y+r*math.sin(a)-.04,z+.02*(rr/.096)**2+.003*math.cos(j*math.pi)))
            for i in range(rows-1):
                for j in range(segs):
                    a=i*(segs+1)+j;ff.append((a,a+1,a+segs+2,a+segs+1))
            mesh('ridged_scallop_shell',vv,ff,material('scallop_shell',(.57,.42,.32),.55,bump=.14),True)
            ball('scallop_meat',(x,y+.006,z+.014),(.046,.040,.017),M['cream'])
            ball('butter_pat',(x,y+.012,z+.033),(.018,.015,.006),M['yellow'])
            herbs_on([(x,y,.034)],z+.039,9)
        for i in range(10):scallop(-.51+(i%5)*.25,.23+(i//5)*.29,zz+.004)
        tray(-.08,-.85,w=2.03,d=.44)
        for i in range(8):scallop(-.83+(i%4)*.49,-.97+(i//4)*.22,1.008)
        squeeze(1.05,.41,mat=sauce)
        tongs(1.14,-.87)

    else:
        tray(-.10,-.84,w=1.9,d=.44)
        ellipsoids('assorted_food',[((-.8+(i%7)*.23,-.96+(i//7)*.19,1.06),(.073,.053,.047)) for i in range(14)],golden,14,10,.045)
        grill()
        tongs(1.15,-.79)

    return {'kind': kind, 'created_helpers': serial[0]}
