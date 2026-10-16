"""Rebuild the editable Japanese ennichi scene. Blender 4.5+ / 5.x.
Run: blender --background --factory-startup --python build_ennichi.py
"""
import bpy, math, random, sys, json, os
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
random.seed(19)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for dat in list(bpy.data.collections):
    if dat.name!='Collection' and dat.users==0: bpy.data.collections.remove(dat)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.cycles.max_bounces=8; scene.cycles.transparent_max_bounces=6
scene.render.resolution_x=1600; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='PNG'
scene.render.fps=30
scene.frame_start=1; scene.frame_end=4801
COL=None

def collection(name):
    global COL
    COL=bpy.data.collections.new(name); scene.collection.children.link(COL); return COL

def meshobj(name, verts, faces, mat, parent=None):
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); COL.objects.link(o)
    if mat: mesh.materials.append(mat)
    if parent: o.parent=parent
    return o

def empty(name,loc=(0,0,0),rotation=0):
    o=bpy.data.objects.new(name,None); COL.objects.link(o); o.location=loc; o.rotation_euler[2]=rotation; return o

# Reuse mesh geometry and use per-object material slots.
CACHE={}
def instance(name,key,creator,loc,scale,mat,parent=None):
    if key not in CACHE:
        creator(); ob=bpy.context.object; CACHE[key]=ob.data; bpy.data.objects.remove(ob,do_unlink=True)
    o=bpy.data.objects.new(name,CACHE[key]); COL.objects.link(o); o.location=loc; o.scale=scale
    if not o.data.materials: o.data.materials.append(mat)
    o.material_slots[0].link='OBJECT'; o.material_slots[0].material=mat
    if parent: o.parent=parent
    return o

def cube(name,loc,dims,mat,parent=None,bevel=.015):
    # Dimensional bevel in the cached base mesh, so no thousands of modifiers.
    key=('cube',tuple(round(x,5) for x in dims),round(bevel,4))
    if key not in CACHE:
        bpy.ops.mesh.primitive_cube_add(); ob=bpy.context.object; ob.dimensions=dims
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if bevel:
            mod=ob.modifiers.new('Soft manufactured edges','BEVEL'); mod.width=min(bevel,min(dims)*.2); mod.segments=2
            bpy.ops.object.modifier_apply(modifier=mod.name)
        CACHE[key]=ob.data; bpy.data.objects.remove(ob,do_unlink=True)
    return instance(name,key,lambda:None,loc,(1,1,1),mat,parent)

def sphere(name,loc,scale,mat,parent=None):
    o=instance(name,'sphere',lambda:bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16),loc,scale,mat,parent)
    for p in o.data.polygons:p.use_smooth=True
    return o

def cylinder(name,loc,radius,depth,mat,parent=None,vertices=24,rotation=None):
    o=instance(name,('cylinder',vertices),lambda:bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=1,depth=1),loc,(radius,radius,depth),mat,parent)
    if rotation:o.rotation_euler=rotation
    for p in o.data.polygons:p.use_smooth=(len(p.vertices)==4)
    return o

def rod(name,a,b,radius,mat,parent=None):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,radius,(b-a).length,mat,parent,vertices=12)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def curve(name,points,radius,mat,parent=None):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=1;d.bevel_depth=radius;d.bevel_resolution=2
    sp=d.splines.new('POLY');sp.points.add(len(points)-1)
    for v,p in zip(sp.points,points):v.co=(*p,1)
    o=bpy.data.objects.new(name,d);COL.objects.link(o);d.materials.append(mat)
    if parent:o.parent=parent
    return o

def torus(name,loc,major,minor,mat,parent=None,rotation=None):
    key=('torus',round(major,5),round(minor,5))
    o=instance(name,key,lambda:bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=24,minor_segments=8),loc,(1,1,1),mat,parent)
    if rotation:o.rotation_euler=rotation
    for p in o.data.polygons:p.use_smooth=True
    return o

def material(name,color,rough=.5,metal=0,noise=0,scale=15):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    if noise:
        tc=n.new('ShaderNodeTexCoord');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=scale;tex.inputs['Detail'].default_value=3
        l.new(tc.outputs['Generated'],tex.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(v*.65 for v in color),1);ramp.color_ramp.elements[1].color=(*(min(1,v*1.18) for v in color),1)
        l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=noise;bump.inputs['Distance'].default_value=.025
        l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    return m
M={}
colors={'steel':(.49,.52,.56),'darksteel':(.09,.10,.105),'wood':(.28,.115,.037),'bamboo':(.59,.39,.14),'white':(.88,.84,.74),'cream':(.93,.81,.53),'red':(.64,.025,.017),'green':(.055,.24,.08),'yellow':(.96,.55,.025),'orange':(.94,.22,.012),'pink':(.96,.24,.44),'blue':(.018,.17,.48),'chocolate':(.092,.031,.016),'bread':(.55,.23,.055),'noodle':(.61,.32,.09),'leaf':(.08,.19,.025),'glass':(.75,.90,.9),'water':(.17,.54,.63),'black':(.014,.017,.021)}
for k,c in colors.items(): M[k]=material(k,c,rough=.29 if k in ['steel','darksteel','red','glass','water'] else .55,metal=.85 if 'steel' in k else 0,noise=.13 if k in ['wood','bread','leaf','bamboo'] else 0)
for k in ['glass','water']:
    bs=M[k].node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=.95;bs.inputs['Roughness'].default_value=.08;bs.inputs['IOR'].default_value=1.333 if k=='water' else 1.45
# Timber grain stretched along the boards.
for k in ['wood','bamboo']:
    nd=M[k].node_tree.nodes;lk=M[k].node_tree.links;tex=next(n for n in nd if n.type=='TEX_NOISE');tex.inputs['Scale'].default_value=5
    mapping=nd.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(2,65,8);tc=next(n for n in nd if n.type=='TEX_COORD');lk.new(tc.outputs['Generated'],mapping.inputs[0]);lk.new(mapping.outputs[0],tex.inputs['Vector'])
M['canvas_red']=material('Weathered vermilion canvas',(.5,.018,.012),.82,noise=.25,scale=120)
M['canvas_cream']=material('Unbleached canvas',(.68,.6,.43),.84,noise=.18,scale=180)
M['canvas_blue']=material('Indigo cotton',(.012,.055,.12),.85,noise=.25,scale=160)
M['gravel']=material('Compacted sandy plaza',(.28,.22,.135),.95,noise=.5,scale=180)
M['concrete']=material('Aged concrete',(.38,.39,.36),.85,noise=.4,scale=55)
M['lamp']=material('Warm paper glow',(1,.61,.25),.62,noise=.1,scale=60)
bs=M['lamp'].node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.32,.075,1);bs.inputs['Emission Strength'].default_value=2
M['lamp_red']=material('Red paper glow',(.65,.035,.016),.6,noise=.12,scale=45)
bs=M['lamp_red'].node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.055,.007,1);bs.inputs['Emission Strength'].default_value=1.2
# Converted text meshes make Japanese lettering portable; font not redistributed.
fontpaths=[p for p in Path('/System/Library/Fonts').glob('*.ttc') if '角' in p.name and 'W6' in p.name]
FONT=bpy.data.fonts.load(str(fontpaths[0])) if fontpaths else bpy.data.fonts.get('Bfont')
def text3d(name,body,loc,size,mat,parent=None,width=None):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.font=FONT;d.align_x='CENTER';d.align_y='CENTER';d.size=size;d.extrude=.0005;d.resolution_u=4
    o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc;o.rotation_euler=(math.pi/2,0,0);d.materials.append(mat)
    if parent:o.parent=parent
    bpy.context.view_layer.update()
    if width and o.dimensions.x>width:o.scale.x*=width/o.dimensions.x
    # Convert through evaluated mesh without an operator or font file dependency.
    deps=bpy.context.evaluated_depsgraph_get();mesh=bpy.data.meshes.new_from_object(o.evaluated_get(deps));loc0=o.location.copy();rot=o.rotation_euler.copy();sc=o.scale.copy()
    bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.curves.remove(d)
    ob=bpy.data.objects.new(name,mesh);COL.objects.link(ob);ob.location=loc0;ob.rotation_euler=rot;ob.scale=sc
    if parent:ob.parent=parent
    return ob

def light(name,loc,power,color,size=2,parent=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc
    if parent:o.parent=parent
    return o

def lantern(name,loc,r=.21,parent=None,red=False):
    mat=M['lamp_red'] if red else M['lamp'];x,y,z=loc
    sphere(name+' paper',loc,(r,r,r*1.23),mat,parent)
    for i in range(-4,5):
        zz=i*r*.23;rr=r*math.sqrt(max(.08,1-(zz/(r*1.24))**2))
        torus(name+' bamboo rib',(x,y,z+zz),rr,.006,M['bamboo'],parent)
    for zz in [-1,1]:cylinder(name+' black collar',(x,y,z+zz*r*1.2),r*.42,.045,M['black'],parent)
    rod(name+' hanger',(x,y,z+r*1.2),(x,y,z+r*1.5),.008,M['black'],parent)

API=dict(cube=cube,sphere=sphere,cylinder=cylinder,rod=rod,curve=curve,torus=torus,M=M)
collection('01 | Ground & 200 m circulation')
# World-projected photogrammetric asphalt PBR with a 3 m repeat.
asphalt=material('Poly Haven | aerial_asphalt_01',(.15,.15,.15),.85)
nd=asphalt.node_tree.nodes;lk=asphalt.node_tree.links;bs=nd.get('Principled BSDF');tc=nd.new('ShaderNodeTexCoord');vm=nd.new('ShaderNodeVectorMath');vm.operation='SCALE';vm.inputs[3].default_value=1/3;lk.new(tc.outputs['Object'],vm.inputs[0])
for fname,target in [('asphalt_diff.jpg','Base Color'),('asphalt_rough.jpg','Roughness'),('asphalt_normal.jpg','Normal')]:
    tex=nd.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(BASE/'assets'/fname));tex.projection='BOX';tex.projection_blend=.15;lk.new(vm.outputs[0],tex.inputs['Vector'])
    if target!='Base Color':tex.image.colorspace_settings.name='Non-Color'
    if target=='Normal':
        normal=nd.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.55;lk.new(tex.outputs['Color'],normal.inputs['Color']);lk.new(normal.outputs[0],bs.inputs[target])
    else:lk.new(tex.outputs['Color'],bs.inputs[target])
cube('Terrain base',(0,0,-.3),(1500,1500,.5),M['gravel'],bevel=0)
cube('Asphalt square',(0,0,-.015),(66,66,.09),asphalt,bevel=0)
cube('Inner plaza | 44m x44m',(0,0,.025),(43.9,43.9,.10),M['gravel'],bevel=.01)
for a in [-1,1]:
    cube('Flush stone border',(a*22,0,.04),(.16,44,.07),M['concrete'])
    cube('Flush stone border',(0,a*22,.04),(44,.16,.07),M['concrete'])
    for p in range(-21,22,3):
        cube('Drain grate',(a*27.7,p,.024),(.19,.65,.014),M['darksteel'],bevel=.003)
        cube('Drain grate',(p,a*27.7,.024),(.65,.19,.014),M['darksteel'],bevel=.003)
# True closed 50 m by 50 m reference path, non-rendering.
collection('00 | Guides (hidden in render)')
route=curve('ROUTE | 50m x 50m | 200m', [(-25,-25,.08),(25,-25,.08),(25,25,.08),(-25,25,.08),(-25,-25,.08)],0,M['yellow'])
route.hide_render=True;route.hide_viewport=True;route['length_m']=200;route['path_width_m']=6;route['side_length_m']=50

FOODS=[('わたあめ','cotton_candy'),('りんご飴','apple_candy'),('焼きそば','yakisoba'),('たこ焼き','takoyaki'),('かき氷','kakigori'),('チョコバナナ','choco_banana'),('たい焼き','taiyaki'),('焼き鳥','yakitori'),('お好み焼き','okonomiyaki'),('からあげ','karaage'),('フライドポテト','potato'),('焼とうもろこし','corn'),('いか焼き','ikayaki'),('みたらし団子','dango'),('クレープ','crepe'),('ベビーカステラ','baby_castella'),('焼せんべい','rice_cracker'),('フランクフルト','frankfurt'),('冷やしきゅうり','cucumber'),('レモネード','lemonade'),('ラムネ','ramune'),('冷たいお茶','tea'),('生ビール','beer'),('焼おにぎり','yakionigiri'),('焼きいも','sweet_potato'),('いちご飴','strawberry_candy'),('ぶどう飴','candied_grapes'),('ソフトクリーム','soft_serve'),('フルーツカップ','fruit_cup'),('ほたて焼き','grilled_scallop')]
GAMES=[('射 的','shooting'),('金魚すくい','goldfish'),('スーパーボール','superball'),('ヨーヨーつり','yoyo'),('輪 投 げ','ring_toss'),('くじびき','lottery'),('スマートボール','smartball'),('缶たおし','can_knockdown'),('あひるすくい','rubber_duck'),('水鉄砲','water_pistol'),('コルク的あて','cork_target'),('千本引き','senbonbiki'),('お め ん','masks'),('かざぐるま','pinwheel'),('駄 菓 子','dagashi'),('おもちゃ','toy_sword'),('宝石すくい','gem_scoop'),('お手玉投げ','beanbag')]
# Mixed food and games along every side; no long repeated row of one type.
menu=[]
for i in range(48):
    if i%8 in (3,5,7):menu.append(GAMES.pop(0))
    else:menu.append(FOODS.pop(0))
from food_props import build_food
from game_props import build_game
food_kinds={x for _,x in [('','cotton_candy'),('','apple_candy'),('','yakisoba'),('','takoyaki'),('','kakigori'),('','choco_banana'),('','taiyaki'),('','yakitori'),('','okonomiyaki'),('','karaage'),('','potato'),('','corn'),('','ikayaki'),('','dango'),('','crepe'),('','baby_castella'),('','rice_cracker'),('','frankfurt'),('','cucumber'),('','lemonade'),('','ramune'),('','tea'),('','beer'),('','yakionigiri'),('','sweet_potato'),('','strawberry_candy'),('','candied_grapes'),('','soft_serve'),('','fruit_cup'),('','grilled_scallop')]}
manifest=[]

def cloth(name,width,y,z,h,mat,parent):
    # Corrugated weighted fabric edge and subtle folds.
    verts=[];nx=60;nz=6
    for j in range(nz+1):
        for i in range(nx+1):
            x=-width/2+width*i/nx;wave=.018*math.sin(i*.84)+.012*math.sin(i*1.92)
            verts.append((x,y+wave*(.4+j/nz),z-h*j/nz+.012*math.sin(i*.55)*j/nz))
    faces=[]
    for j in range(nz):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    o=meshobj(name,verts,faces,mat,parent)
    for p in o.data.polygons:p.use_smooth=True
    return o

for i,(title,kind) in enumerate(menu):
    side=i//12;k=i%12;u=-21.175+k*3.85
    loc,angle=[((u,-29.8,0),math.pi),((29.8,u,0),-math.pi/2),((-u,29.8,0),0),((-29.8,-u,0),math.pi/2)][side]
    collection(f'{i+1:02d} | {title}')
    p=empty(f'STALL_{i+1:02d}_{kind}',loc,angle);p['shop_name']=title;p['kind']=kind;p['footprint_m']='3.6 x 3.0'
    manifest.append(dict(id=i+1,name=title,kind=kind,side=['南','東','北','西'][side],x=loc[0],y=loc[1]))
    # Steel frame, concrete ballast, cable ties and gabled canvas.
    for x in [-1.72,1.72]:
        for y in [-1.38,1.36]:
            rod('Galvanised tent leg',(x,y,.08),(x,y,2.73),.033,M['steel'],p)
            cube('Concrete leg weight',(x,y,.14),(.31,.29,.25),M['concrete'],p,.04)
            for z in [1.05,2.32]:torus('Black cable tie',(x,y,z),.038,.006,M['black'],p)
        rod('Roof ridge support',(x,-1.44,2.76),(x,0,3.3),.025,M['steel'],p)
        rod('Roof ridge support',(x,0,3.3),(x,1.48,2.76),.025,M['steel'],p)
    for y,z in [(-1.46,2.73),(0,3.30),(1.49,2.73)]:rod('Cross rail',(-1.85,y,z),(1.85,y,z),.028,M['steel'],p)
    roofmat=[M['canvas_red'],M['canvas_blue'],M['canvas_cream'],M['canvas_red']][i%4]
    for sy in [-1,1]:
        vv=[];ff=[]
        for yy in range(10):
            t=yy/9
            for xx in range(41):
                x=-1.85+3.7*xx/40
                vv.append((x,sy*1.6*t,3.32-.57*t-.03*math.sin(xx*math.pi/5)*math.sin(t*math.pi)))
        for yy in range(9):
            for xx in range(40):a=yy*41+xx;ff.append((a,a+1,a+42,a+41))
        o=meshobj('Canvas roof with sag',vv,ff,roofmat,p)
        for poly in o.data.polygons:poly.use_smooth=True
    cloth('Front canvas valance',3.7,-1.60,2.78,.19,roofmat,p)
    cloth('Rear canvas wall',3.44,1.37,2.62,2.35,M['canvas_cream'] if i%3 else M['canvas_blue'],p)
    # Fold-out prep table, rear supplies and crates.
    cube('Rear work surface',(0,1.08 if kind in ['goldfish','superball','yoyo','rubber_duck','gem_scoop'] else .71,.97),(3.1,.396 if kind in ['goldfish','superball','yoyo','rubber_duck','gem_scoop'] else 1.1,.055),M['steel'],p)
    for x in [-1.25,1.25]:
        rod('Table leg',(x,.73,.05),(x,.73,.94),.025,M['steel'],p)
        cube('Storage crate',(x,.78,.25),(.47,.4,.36),M['blue'] if i%2 else M['red'],p,.024)
        for dz in [-.10,0,.1]:cube('Crate rib',(x,.569,.25+dz),(.44,.025,.025),M['darksteel'],p,.002)
    # Pools have a purpose-built low front tub, no intersecting counter.
    pool=kind in ['goldfish','superball','yoyo','rubber_duck','gem_scoop']
    if not pool:
        cube('Serving counter',(0,-.87,.92),(3.38,.82,.075),M['steel'] if kind in food_kinds else M['wood'],p)
        for x in [-1.5,1.5]:
            for y in [-1.17,-.55]:rod('Counter leg',(x,y,.04),(x,y,.90),.026,M['steel'],p)
        curtain=cloth('Red and white striped waist cloth',3.36,-1.295,.87,.76,M['canvas_cream'],p)
        curtain.data.materials.append(M['canvas_red'])
        for poly in curtain.data.polygons:
            col=poly.index%60;poly.material_index=int((col//5)%2==0)
    # Main backlit-style painted fabric sign and smaller menu plaques.
    signmat=M['canvas_cream'] if i%3 else M['canvas_red']
    cube('Main sign fabric',(0,-1.624,2.49),(3.35,.025,.54),signmat,p,.002)
    text3d('Japanese shop lettering',title,(0,-1.65,2.50),.45,M['red'] if i%3 else M['white'],p,width=3.06)
    text3d('Shop number',f'{i+1:02d}',(-1.43,-1.65,2.32),.085,M['blue'] if i%3 else M['white'],p)
    for x in [-1.5,1.5]:lantern('Shop lantern',(x,-1.62,2.0),.14,p,red=i%2==0)
    cube('Price board',(1.24,-.9 if pool else -1.22,1.12 if pool else 1.17),(.41,.025,.42),M['cream'],p,.002)
    text3d('Price text',('一回' if kind not in food_kinds else '一つ')+'\n五百円',(1.24,-.92 if pool else -1.24,1.13 if pool else 1.18),.115,M['black'],p,width=.35)
    # Tubular shop lamp and warm area source.
    rod('Fluorescent housing',(-.95,-.45,2.5),(.95,-.45,2.5),.026,M['lamp'],p)
    light('Warm stall light',(0,-.32,2.52),110,(1,.64,.36),2.0,p)
    if kind in food_kinds:build_food(kind,p,API)
    else:build_game(kind,p,API)
    # Narrow nobori flags stay inside stall footprint.
    if i%3==0:
        rod('Nobori pole',(-1.73,-1.35,.12),(-1.73,-1.35,3.5),.017,M['steel'],p)
        rod('Nobori top crossbar',(-1.73,-1.35,3.43),(-1.17,-1.35,3.43),.012,M['steel'],p)
        o=cloth('Fluttering nobori',.48,-1.33,3.42,1.13,M['canvas_red'] if i%2 else M['canvas_blue'],p);o.location.x=-1.46
        text3d('Nobori text','縁\n日',(-1.46,-1.38,2.90),.3,M['white'],p)
    print('Built stall',i+1,title,flush=True)

collection('60 | Bon odori yagura')
yagura=empty('YAGURA | central 6m platform')
# Lower deck, individually grained floor planks.
for x in [-2.65,2.65]:
    for y in [-2.65,2.65]:
        cube('Main timber post',(x,y,2.73),(.19,.19,5.4),M['wood'],yagura)
        cube('Stone post foot',(x,y,.15),(.4,.4,.29),M['concrete'],yagura,.025)
for i in range(28):cube('Platform floorboard',(-2.87+i*.212,0,1.35),(.20,6,.14),M['wood'],yagura,.008)
for side in range(4):
    parent=empty('Yagura side',rotation=side*math.pi/2);parent.parent=yagura
    for x in [-2.7,2.7]:rod('Diagonal timber brace',(x,-2.7,.25),(-x,-2.7,1.23),.055,M['wood'],parent)
    o=cloth('Kohaku stage skirt',6,-3.01,1.31,1.13,M['canvas_cream'],parent);o.data.materials.append(M['canvas_red'])
    for poly in o.data.polygons:poly.material_index=int((poly.index%60//5)%2==0)
    for z in [1.8,2.38]:
        if side==2:
            for x in [-1.74,1.74]:cube('Safety railing',(x,-2.75,z),(2.17,.09,.095),M['red'],parent)
        else:cube('Safety railing',(0,-2.75,z),(5.65,.09,.095),M['red'],parent)
    for x in [-2.65,-1.75,-.9,0,.9,1.75,2.65]:
        if side==2 and x==0:continue
        cube('Railing spindle',(x,-2.75,1.91),(.07,.07,1.0),M['wood'],parent)
    cube('Upper beam',(0,-2.65,5.1),(5.7,.2,.24),M['wood'],parent)
    for x in [-2,-1,0,1,2]:lantern('Yagura lantern',(x,-2.88,4.65),.22,parent,red=abs(x)%2==0)
    # Upper signage.
    for x in [-1.3,1.3]:rod('Festival sign suspension',(x,-2.89,4.25),(x,-2.89,5.1),.009,M['black'],parent)
    cube('Festival title backing',(0,-2.89,3.87),(3.15,.04,.76),M['canvas_cream'],parent)
    text3d('Festival title','納 涼 盆 踊 り',(0,-2.921,3.89),.42,M['black'],parent,width=2.95)
# Hip roof with realistic raised ridge and battens.
rv=[(-3.45,-3.45,5.25),(3.45,-3.45,5.25),(3.45,3.45,5.25),(-3.45,3.45,5.25),(-1.6,0,6.65),(1.6,0,6.65)]
meshobj('Yagura hipped canvas roof',rv,[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4)],M['canvas_red'],yagura)
for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(0,4),(1,5),(2,5),(3,4)]:rod('Roof seam',rv[a],rv[b],.022,M['bamboo'],yagura)
# Access stair at north, 7 treads, uninterrupted rise to platform.
for i in range(7):cube('Yagura stair',(0,4.85-i*.285,(i+1)*.195/2),(1.35,.32,.195*(i+1)),M['wood'],bevel=.008)
for x in [-.68,.68]:
    rod('Stair handrail',(x,5.02,.9),(x,3.08,2.15),.035,M['wood'])
    for y,z in [(5.02,.4),(3.08,1.25)]:rod('Stair baluster',(x,y,z),(x,y,z+.9),.035,M['wood'])
# Taiko drum on timber trestle, heads, metal tacks, sticks.
for x in [-.62,.62]:
    rod('Taiko stand',(x,-.6,1.43),(x,.2,2.35),.065,M['wood'])
    rod('Taiko stand',(x,.6,1.43),(x,-.2,2.35),.065,M['wood'])
cylinder('Taiko lacquered barrel',(0,0,2.55),.56,.85,M['red'],vertices=48,rotation=(math.pi/2,0,0))
for y in [-.445,.445]:
    cylinder('Taiko skin',(0,y,2.55),.548,.035,M['cream'],vertices=48,rotation=(math.pi/2,0,0))
    torus('Taiko hoop',(0,y,2.55),.54,.03,M['black'],rotation=(math.pi/2,0,0))
    for a in range(24):
        t=a*math.tau/24;sphere('Taiko tack',(.51*math.sin(t),y*1.045,2.55+.51*math.cos(t)),(.015,.012,.015),M['steel'])
rod('Drumstick',(-.45,-.95,1.53),(.35,-.86,1.57),.018,M['bamboo']);rod('Drumstick',(-.2,-1.05,1.53),(.57,-.90,1.57),.018,M['bamboo'])
for x in [-1.9,1.9]:
    cube('PA loudspeaker',(x,1.6,1.85),(.4,.35,.75),M['black'],bevel=.03)
    for z in [1.7,2.02]:cylinder('Speaker cone',(x,1.414,z),.14,.015,M['darksteel'],rotation=(math.pi/2,0,0))
light('Stage warm wash',(0,0,4.95),950,(1,.55,.23),4)

collection('61 | Lantern canopy')
rod('Central lantern mast',(0,0,5.15),(0,0,7.75),.055,M['wood'])
rod('Mast support beam X',(-2.7,0,5.18),(2.7,0,5.18),.075,M['wood'])
rod('Mast support beam Y',(0,-2.7,5.18),(0,2.7,5.18),.075,M['wood'])
for j in range(8):
    angle=j*math.pi/4;dx,dy=math.cos(angle),math.sin(angle);length=20 if j%2==0 else 27
    end=(dx*length,dy*length,5.8)
    rod('Lantern mast',(end[0],end[1],.07),end,.055,M['wood'])
    pts=[]
    for k in range(65):
        t=k/64;r=3+t*(length-3);pts.append((dx*r,dy*r,6.05*(1-t)+5.8*t-1.05*math.sin(math.pi*t)))
    curve('Cable to central mast',[(0,0,7.65),pts[0]],.013,M['black'])
    curve('Sagging festival cable',pts,.013,M['black'])
    n=int((length-3)/1.35)
    for k in range(n):
        t=(k+.5)/n;r=3+t*(length-3);z=6.05*(1-t)+5.8*t-1.05*math.sin(math.pi*t)
        lantern('Suspended paper chochin',(dx*r,dy*r,z-.33),.205,red=k%3==0)
# Perimeter lantern strings on the inner edge leave walkway head clearance >3.6 m.
for j in range(4):
    pa=empty('Perimeter string',rotation=j*math.pi/2)
    for x in [-21,0,21]:rod('Perimeter pole',(x,21.2,.07),(x,21.2,4.2),.045,M['wood'],pa)
    for seg in [-1,1]:
        pts=[(seg*21*t,21.2,4.2-.4*math.sin(math.pi*t)) for t in [i/40 for i in range(41)]]
        curve('Perimeter catenary',pts,.009,M['black'],pa)
        for k in range(13):
            t=(k+.5)/13;lantern('Perimeter lantern',(seg*21*t,21.2,4.2-.4*math.sin(math.pi*t)-.24),.15,pa,red=k%3==0)

collection('70 | Landscape & rest areas')
from landscape import build_landscape
build_landscape(API)
for mesh in list(bpy.data.meshes):
    if not mesh.name.startswith('Landscape_IndividualLeafData_'):continue
    rng=random.Random(2019+sum(map(ord,mesh.name)))
    oldverts=[v.co.copy() for v in mesh.vertices];oldfaces=[list(f.vertices) for f in mesh.polygons];indices=[f.material_index for f in mesh.polygons]
    verts=list(oldverts);faces=list(oldfaces);matids=list(indices)
    for layer in range(2):
        offset=len(verts)
        for i in range(0,len(oldverts),7):
            shift=Vector((rng.uniform(-.20,.20),rng.uniform(-.20,.20),rng.uniform(-.16,.16)))
            origin=oldverts[i]
            verts.extend(origin+(v-origin)*1.1+shift for v in oldverts[i:i+7])
        faces.extend([[v+offset for v in f] for f in oldfaces]);matids.extend(indices)
    mats=list(mesh.materials)
    mesh.clear_geometry();mesh.from_pydata(verts,[],faces);mesh.update()
    for p,idx in zip(mesh.polygons,matids):p.material_index=idx


collection('80 | Cameras & lighting')
# Dusk sky from photographed CC0 HDRI, packed in the blend.
world=bpy.data.worlds.new('Dusk | Poly Haven kloppenheim_06_puresky');scene.world=world;world.use_nodes=True
n=world.node_tree.nodes;l=world.node_tree.links;bg=n.get('Background');bg.inputs['Strength'].default_value=.48
env=n.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(BASE/'assets/sunset.hdr'))
tc=n.new('ShaderNodeTexCoord');mp=n.new('ShaderNodeMapping');mp.inputs['Rotation'].default_value[2]=.7;l.new(tc.outputs['Generated'],mp.inputs['Vector']);l.new(mp.outputs[0],env.inputs['Vector']);l.new(env.outputs[0],bg.inputs['Color'])
d=bpy.data.lights.new('Last evening sunlight','SUN');d.energy=1.4;d.color=(1,.69,.43);d.angle=.08
o=bpy.data.objects.new('Last evening sunlight',d);COL.objects.link(o);o.rotation_euler=(math.radians(76),math.radians(-15),math.radians(-42))

def camera(name,loc,target,lens=30):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=350;d.clip_start=.05;return o
hero=camera('01 | Festival overview',(65,-73,57),(0,0,0),42)
walk=camera('02 | Walk - sweets & games',(-15.8,-24.1,1.66),(-8,-29.5,1.55),26)
center=camera('03 | Yagura from approach',(11,-17,1.67),(0,0,3),29)
foodcam=camera('04 | Food stalls close-up',(-19.25,-23.8,1.65),(-19.25,-29.6,1.62),28)
plan=camera('05 | Orthographic site plan',(0,0,105),(0,0,0));plan.data.type='ORTHO';plan.data.ortho_scale=90
loop=camera('06 | WALKTHROUGH - 200m / 160s',(-25,-25,1.65),(25,-25,1.65),24)
# Four equal 50m legs. Linear position interpolation ensures exact 200m loop.
for frame,point,target in [(1,(-25,-25,1.65),(25,-25,1.65)),(1201,(25,-25,1.65),(25,25,1.65)),(2401,(25,25,1.65),(-25,25,1.65)),(3601,(-25,25,1.65),(-25,-25,1.65)),(4801,(-25,-25,1.65),(25,-25,1.65))]:
    loop.location=point;loop.keyframe_insert(data_path='location',frame=frame)
# Rotation eased around corners; along each side look at stalls at a slight angle.
for start,ang in [(1,math.pi/2),(1201,math.pi),(2401,3*math.pi/2),(3601,2*math.pi),(4801,5*math.pi/2)]:
    # Camera local -Z forward, Z-up transform from travel vector.
    direction=Vector((math.sin(ang),-math.cos(ang),-.015));loop.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();loop.keyframe_insert(data_path='rotation_euler',frame=start)
# Blender 5 action slots API.
if loop.animation_data:
    action=loop.animation_data.action
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for key in fc.keyframe_points:key.interpolation='LINEAR' if fc.data_path=='location' else 'CONSTANT'
    except Exception:pass
scene.frame_set(1);scene.camera=hero
for name,frame in [('SOUTH / sweets',1),('EAST / food & games',1201),('NORTH / cool treats',2401),('WEST / games',3601)]:scene.timeline_markers.new(name,frame=frame)
# Store startup view aligned to camera and sensible walking speed.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_end=350
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.overlay.show_relationship_lines=False
try:bpy.context.preferences.inputs.walk_navigation.walk_speed=1.4
except:pass
# Helpful metadata saved inside file.
scene['design']='Japanese traditional ennichi / 48 unique stalls / central bon odori yagura'
scene['route']='Centerline square 50 x 50 m, 200 m total; clear walking width 6 m.'
scene['photorealism']='Physical geometry and materials; PBR asphalt and HDRI. Procedural original stall assets.'
scene['walk_mode']='Select a ground camera; Numpad 0, then Shift+` for Walk Navigation.'
bpy.data.texts.new('READ ME - 日本語').write('四辺の通路中心線は50m四方・一周200m。通路幅6m。屋台48種、中央やぐら。\n単位m。カメラ02〜04は目線高さ。カメラ06で周回アニメーション160秒。\n各屋台は個別コレクションと親Emptyで移動できます。\n背景・地面テクスチャはファイルにパック済み。日本語文字はメッシュ化済み。\n人・音声・ゲーム動作・当たり判定・群衆は含みません。\n')
# Pack textures and eliminate external font dependency.
bpy.ops.file.pack_all()
for font in list(bpy.data.fonts):
    if font.name!='Bfont' and font.users==0:bpy.data.fonts.remove(font)
scene.render.filepath=str(BASE/'01_overview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'ennichi_50m.blend'),compress=True)
json.dump(dict(stalls=manifest,route=dict(side_m=50,length_m=200,width_m=6),objects=len(scene.objects),meshes=len(bpy.data.meshes)),open(BASE/'scene_manifest.json','w'),ensure_ascii=False,indent=2)
print('SCENE_SAVED',len(scene.objects),'objects',flush=True)
