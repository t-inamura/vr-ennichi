"""Detailed, original festival game props. Local booth origin; shoppers face +Y.

build_game(kind, parent, api) adds editable mesh props. api is a dictionary or
namespace containing M and cube, sphere, cylinder, rod, curve and torus helpers.
All dimensions are metres. No external image or model dependencies.
"""
import math
import random
import bpy


def build_game(kind, parent, api):
    object_count_before = len(bpy.data.objects)
    get = api.get if isinstance(api, dict) else lambda k: getattr(api, k)
    M = get("M")
    cube, sphere, cylinder, rod, curve, torus = [get(n) for n in
        ("cube", "sphere", "cylinder", "rod", "curve", "torus")]
    rng = random.Random(430 + sum(map(ord, kind)))
    prefix = "Game_" + kind + "_"
    serial = [0]

    def name(n):
        serial[0] += 1
        return prefix + str(serial[0]).zfill(3) + "_" + n

    def box(n, p, d, m, bevel=.012):
        return cube(name(n), p, d, m, parent=parent, bevel=bevel)

    def ball(n, p, s, m):
        return sphere(name(n), p, s, m, parent=parent)

    def cyl(n, p, r, h, m, vertices=24, rotation=None):
        return cylinder(name(n), p, r, h, m, parent=parent,
                        vertices=vertices, rotation=rotation)

    def stick(n, a, b, r, m):
        return rod(name(n), a, b, r, m, parent=parent)

    def line(n, pts, r, m):
        return curve(name(n), pts, r, m, parent=parent)

    def ring(n, p, r, thickness, m, rotation=None):
        return torus(name(n), p, r, thickness, m, parent=parent,
                     rotation=rotation)

    def mesh(n, vs, fs, mat, smooth=False):
        data = bpy.data.meshes.new(name(n) + "Mesh")
        data.from_pydata(vs, [], fs)
        data.materials.append(mat)
        data.update()
        ob = bpy.data.objects.new(name(n), data)
        collection = parent.users_collection[0] if parent and parent.users_collection else bpy.context.scene.collection
        collection.objects.link(ob)
        ob.parent = parent
        for poly in data.polygons:
            poly.use_smooth = smooth
        return ob

    def material(n, color, rough=.35, transmission=0, metallic=0):
        n = "Ennichi_" + n
        if n in bpy.data.materials:
            return bpy.data.materials[n]
        mat = bpy.data.materials.new(n)
        mat.diffuse_color = (*color, 1)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        return mat

    palette = [M[c] for c in ("red", "yellow", "blue", "pink", "green", "orange")]
    vinyl = [material("Vinyl_" + str(i), c, .23, .12) for i, c in enumerate([
        (.72, .026, .07), (.97, .68, .035), (.025, .36, .72),
        (.91, .15, .37), (.08, .57, .17), (.92, .29, .035)])]
    netmat = material("Paper_scoop", (.87, .90, .83), .87)
    fishmat = material("Goldfish_orange", (.97, .19, .025), .21)
    corkmat = material("Cork", (.51, .30, .14), .93)

    def tray(x, y, z, w, d, mat=M["steel"]):
        box("tray_bottom", (x, y, z), (w, d, .025), mat, .02)
        for sx in (-1, 1):
            box("tray_rim", (x+sx*w/2, y, z+.035), (.024, d, .075), mat)
        for sy in (-1, 1):
            box("tray_rim", (x, y+sy*d/2, z+.035), (w, .024, .075), mat)

    def prize(x, y, z, size=.22, color=None):
        color = color or rng.choice(palette)
        box("prize_carton", (x, y, z+size*.58), (size, size*.7, size*1.16), color)
        box("prize_print_band", (x, y-size*.354-.003, z+size*.65),
            (size*.77, .006, size*.26), M["cream"], .001)
        # Printed colour block and small stars stay generic and original.
        box("prize_print_mark", (x-size*.2, y-size*.364, z+size*.69),
            (size*.14, .006, size*.12), M["red"], .001)
        for k in range(3):
            box("prize_type_line", (x+size*.10, y-size*.365, z+size*(.73-.07*k)),
                (size*.25, .005, .006), M["darksteel"], 0)

    def teddy(x, y, z, color):
        ball("toy_body", (x,y,z+.18), (.12,.09,.16), color)
        ball("toy_head", (x,y-.008,z+.38), (.13,.10,.12), color)
        for s in (-1,1):
            ball("toy_ear", (x+s*.10,y,z+.47), (.051,.035,.053), color)
            ball("toy_paw", (x+s*.12,y-.025,z+.15), (.05,.046,.085), color)
            ball("toy_eye", (x+s*.045,y-.102,z+.399), (.012,.008,.013), M["black"])
        ball("toy_muzzle", (x,y-.099,z+.35), (.05,.025,.035), M["cream"])

    def prize_rack(full=True):
        box("backstop_fabric", (0,1.255,1.83), (3.05,.06,1.55), M["darksteel"])
        for x in (-1.46,1.46):
            box("rack_upright", (x,1.02,1.64), (.08,.08,1.77), M["wood"])
        for r, z in enumerate((1.21,1.73,2.25)):
            box("prize_shelf", (0,1.03,z), (3.04,.47,.052), M["wood"])
            count = 9 if full else 6
            for j in range(count):
                x = -1.27+j*2.54/(count-1)
                if r==2 and j in (2,6):
                    teddy(x,1.0,z+.025,rng.choice(vinyl))
                else:
                    prize(x,.96,z+.031,.19+rng.random()*.065)

    def scoop(x,y,z,angle=0):
        r=.115
        ring("scoop_rim", (x,y,z), r,.009,M["pink"])
        # A single mesh contains the fine crossing mesh of the paper scoop.
        vs,fs=[],[]
        for axis in (0,1):
            for v in range(-4,5):
                off=v*.023
                half=math.sqrt(max(0,r*r-off*off))
                a,b=((-half,off),(half,off)) if axis==0 else ((off,-half),(off,half))
                nx,ny=(0,.0015) if axis==0 else (.0015,0)
                k=len(vs)
                vs.extend([(x+a[0]-nx,y+a[1]-ny,z), (x+b[0]-nx,y+b[1]-ny,z),
                           (x+b[0]+nx,y+b[1]+ny,z),(x+a[0]+nx,y+a[1]+ny,z)])
                fs.append((k,k+1,k+2,k+3))
        mesh("scoop_net",vs,fs,netmat)
        stick("scoop_handle", (x,y-r,z), (x+math.sin(angle)*.15,y-r-.24,z+.026),.016,M["pink"])

    def pool():
        # Small domestic festival trough: blue moulded tub, exposed water,
        # rolled perimeter and a sturdy trestle stand.
        for x in (-1.14,1.14):
            for y in (-.77,.39):
                box("pool_trestle", (x,y,.36), (.085,.085,.68), M["steel"])
            stick("pool_crossbrace",(x,-.77,.13),(x,.39,.66),.017,M["steel"])
        box("pool_blue_base", (0,-.18,.66), (2.82,1.54,.09), M["blue"],.065)
        for x in (-1.38,1.38):
            box("pool_wall", (x,-.18,.79), (.065,1.51,.23), M["blue"],.03)
        for y in (-.91,.55):
            box("pool_wall", (0,y,.79), (2.8,.065,.23), M["blue"],.03)
        box("visible_water",(0,-.18,.854),(2.71,1.39,.018),M["water"],.01)
        for y in (-.935,.575):
            stick("rolled_pool_lip",(-1.38,y,.91),(1.38,y,.91),.021,M["blue"])
        for x in (-1.395,1.395):
            stick("rolled_pool_lip",(x,-.915,.91),(x,.565,.91),.021,M["blue"])

    def fish(x,y,z,theta,scale=1):
        def p(a,b,c):
            return (x+scale*(a*math.cos(theta)-b*math.sin(theta)),
                    y+scale*(a*math.sin(theta)+b*math.cos(theta)),z+c*scale)
        o=ball("goldfish_body",p(0,0,0),(.115*scale,.046*scale,.042*scale),fishmat)
        o.rotation_euler[2]=theta
        # Double triangular tail, erect dorsal fin, two pectoral fins.
        fin_verts=[p(-.08,0,0),p(-.20,-.078,.007),p(-.17,0,.017),p(-.20,.078,.007),
                   p(-.05,0,.032),p(.045,0,.037),p(-.026,0,.093),
                   p(.021,-.024,0),p(-.03,-.08,-.014),p(-.044,-.017,-.005),
                   p(.021,.024,0),p(-.03,.08,-.014),p(-.044,.017,-.005)]
        mesh("goldfish_fins_and_fan_tail",fin_verts,[(0,1,2),(0,2,3),(4,5,6),(7,8,9),(10,11,12)],M["orange"])
        for side in (-1,1):
            ball("fish_eye",p(.071,side*.036,.013),(.01*scale,.01*scale,.01*scale),M["black"])
        # Water surface ripple catches light without an opaque graphic.
        if rng.random()<.3:
            ring("fish_surface_ripple",p(.03,0,.055),.13*scale,.0009,M["glass"])

    def rifle(x,y,z):
        # A cork-gallery toy laid sideways across the counter. The recognizable
        # stock is a bevelled mesh rather than a single rectangular prism.
        profile=[(-.47,-.07),(-.43,.08),(-.19,.075),(-.08,.04),(.08,.035),
                 (.08,-.018),(-.03,-.025),(-.07,-.12),(-.14,-.12),(-.17,-.032)]
        vs=[(x+a,y+b,z+c) for b in (-.034,.034) for a,c in profile]
        N=len(profile)
        fs=[tuple(range(N-1,-1,-1)),tuple(range(N,N*2))]
        fs += [(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
        o=mesh("cork_rifle_wood_stock",vs,fs,M["wood"])
        mod=o.modifiers.new("Rounded stock edges","BEVEL");mod.width=.01;mod.segments=2
        stick("toy_barrel",(x-.04,y,z+.045),(x+.51,y,z+.045),.018,M["darksteel"])
        stick("cork_in_muzzle",(x+.51,y,z+.045),(x+.54,y,z+.045),.021,corkmat)
        ring("trigger_guard",(x-.055,y,z-.055),.043,.007,M["steel"],(math.pi/2,0,0))
        box("butt_cap",(x-.459,y,z+.008),(.018,.079,.14),M["darksteel"])

    def duck(x,y,z,s=.10):
        ball("duck_body",(x,y,z),(s,s*.78,s*.62),M["yellow"])
        ball("duck_head",(x,y-s*.38,z+s*.69),(s*.57,s*.51,s*.57),M["yellow"])
        ball("duck_beak",(x,y-s*.86,z+s*.59),(s*.39,s*.32,s*.16),M["orange"])
        for side in (-1,1):
            ball("duck_eye",(x+side*s*.36,y-s*.69,z+s*.79),(s*.067,)*3,M["black"])

    def tin(x,y,z,col):
        cyl("tin_can",(x,y,z+.096),.086,.192,col)
        for zz in (z+.008,z+.186):
            ring("tin_rolled_seam",(x,y,zz),.087,.006,M["steel"])
        box("tin_label",(x,y-.086,z+.098),(.10,.007,.088),M["cream"],.004)

    if kind in ("goldfish","superball","yoyo","rubber_duck","gem_scoop"):
        pool()
        if kind=="goldfish":
            for _ in range(17):
                fish(rng.uniform(-1.15,1.15),rng.uniform(-.71,.36),.817,rng.random()*math.tau,rng.uniform(.65,1.0))
            for x in (-1.11,-.70,.87):
                scoop(x,-1.16,.937)
            for x in (1.03,1.26):
                cyl("take_home_bowl",(x,.8,1.04),.15,.1,M["cream"])
        elif kind=="superball":
            for _ in range(75):
                x,y=rng.uniform(-1.23,1.23),rng.uniform(-.76,.42)
                rr=rng.uniform(.031,.068)
                ball("floating_superball",(x,y,.854+rr*.6),(rr,rr,rr),rng.choice(vinyl))
            for x in (-.95,.2,1): scoop(x,-1.15,.94)
        elif kind=="yoyo":
            for j in range(21):
                x=-1.08+(j%7)*.35+rng.uniform(-.025,.025)
                y=-.68+(j//7)*.40
                c=j%len(vinyl)
                ball("water_yoyo_balloon",(x,y,.971),(.137,.137,.154),vinyl[c])
                cyl("balloon_tied_neck",(x,y,1.12),.022,.04,vinyl[c])
                line("yoyo_rubber_loop",[(x,y,1.14),(x+.025,y,1.30),(x+.06,y,1.38),(x+.08,y,1.26),(x,y,1.14)],.0025,M["cream"])
                for zz in (-.03,.045):
                    pts=[]
                    for a in range(17):
                        t=a*math.tau/16
                        pts.append((x+.134*math.cos(t),y+.134*math.sin(t),.98+zz+.012*math.sin(3*t)))
                    line("painted_yoyo_swirl",pts,.0035,M["cream"])
            for x in (-1,1):
                stick("yoyo_fishing_hook",(x,-1.19,.94),(x+.12,-.91,.95),.005,M["steel"])
        elif kind=="rubber_duck":
            for j in range(19):
                duck(-1.13+(j%7)*.36,-.66+(j//7)*.42,.92,.087)
            for x in (-1.1,1.1):
                stick("duck_fishing_rod",(x,-1.11,.96),(x*.5,.05,1.1),.012,M["bamboo"])
                line("duck_fishing_line",[(x*.5,.05,1.1),(x*.5,.05,.94)],.002,M["cream"])
        else:
            for _ in range(90):
                rr=rng.uniform(.025,.062)
                ob=ball("polished_scooping_gem",(rng.uniform(-1.22,1.22),rng.uniform(-.74,.39),.836),
                        (rr,rr*.73,rr*.55),rng.choice(vinyl))
                ob.rotation_euler[2]=rng.random()*math.tau
            for x in (-1,0,1): scoop(x,-1.15,.94)

    elif kind=="shooting":
        prize_rack()
        for x,y in ((-.79,-.81),(.38,-.82)):
            rifle(x,y,1.08)
        tray(1.19,-.77,1.0,.35,.35,M["wood"])
        for _ in range(12):
            cyl("spare_cork",(rng.uniform(1.06,1.3),rng.uniform(-.89,-.65),1.045),.018,.035,corkmat,12)

    elif kind=="ring_toss":
        box("ring_toss_table",(0,.30,1.04),(2.63,1.5,.13),M["green"])
        for row in range(3):
            for col in range(6):
                x=-1.03+col*.42;y=-.15+row*.43
                cyl("target_bottle_body",(x,y,1.25),.065,.30,palette[(col+row)%6])
                cyl("target_bottle_neck",(x,y,1.44),.026,.10,M["glass"])
                ring("bottle_lip",(x,y,1.495),.027,.009,M["cream"])
                if row==1:
                    box("target_number_plate",(x,y-.075,1.29),(.07,.008,.10),M["cream"])
        for col in range(3):
            for j in range(4):
                ring("throwing_ring",(-.92+col*.61,-.91,1.005+j*.022),.155,.013,palette[col])

    elif kind=="lottery":
        # Octagonal garapon raffle tumbler and its crank.
        for x in (-.52,.52):
            stick("raffle_A_frame",(x-.18,.12,1.01),(x,.12,1.67),.038,M["wood"])
            stick("raffle_A_frame",(x+.18,.12,1.01),(x,.12,1.67),.038,M["wood"])
        cyl("octagonal_raffle_drum",(0,.12,1.60),.39,.60,M["wood"],8,(0,math.pi/2,0))
        for x in (-.305,.305):
            ring("drum_metal_band",(x,.12,1.60),.366,.022,M["steel"],(0,math.pi/2,0))
        stick("raffle_axle",(-.66,.12,1.60),(.73,.12,1.60),.026,M["steel"])
        stick("crank_arm",(.73,.12,1.60),(.73,.12,1.37),.019,M["steel"])
        stick("crank_wood_handle",(.73,.12,1.37),(.91,.12,1.37),.034,M["wood"])
        box("drum_ball_hatch",(0,-.246,1.45),(.145,.028,.115),M["black"])
        tray(-.17,-.69,1.0,.88,.49,M["wood"])
        for j in range(16):
            ball("raffle_ball",(-.49+(j%5)*.15,-.85+(j//5)*.11,1.049),(.027,)*3,palette[j%6] if j<6 else M["white"])
        for j in range(5):
            box("ticket_stack",(1.12,-.73,1.0+j*.004),(.32,.17,.005),M["cream"],.001)
        for x in (-1.1,-.70,.73,1.16): prize(x,1.02,1.1,.27)

    elif kind=="smartball":
        # Two inclined, glass-fronted vintage pachinko / smartball boards.
        for ox in (-.76,.76):
            y0,y1=-.84,.94;z0,z1=1.07,1.65
            vs=[(ox-.62,y0,z0),(ox+.62,y0,z0),(ox+.62,y1,z1),(ox-.62,y1,z1)]
            mesh("inclined_smartball_playfield",vs,[(0,1,2,3)],M["cream"])
            for sx in (-1,1):
                stick("smartball_side_rail",(ox+sx*.65,y0,z0),(ox+sx*.65,y1,z1),.039,M["wood"])
            for y,z in ((y0,z0),(y1,z1)):
                stick("smartball_end_rail",(ox-.66,y,z),(ox+.66,y,z),.04,M["wood"])
            for row in range(7):
                y=-.55+row*.205;z=z0+(y-y0)/(y1-y0)*(z1-z0)
                for col in range(5):
                    x=ox-.41+col*.205+(row%2)*.036
                    cyl("smartball_brass_pin",(x,y,z+.025),.008,.052,M["steel"],12)
                if row%2==0:
                    for x in (ox-.30,ox+.30):
                        tilt=math.atan((z1-z0)/(y1-y0))
                        cyl("score_hole",(x,y+.065,z+.043),.039,.005,M["black"],24,(tilt,0,0))
                        ring("score_hole_brass_rim",(x,y+.065,z+.048),.042,.005,M["yellow"],(tilt,0,0))
            for j in range(5):
                ball("smartball_white_marble",(ox-.35+j*.14,y0+.06,z0+.045),(.035,)*3,M["white"])
            stick("spring_plunger",(ox+.51,-1.01,1.06),(ox+.51,-.58,1.20),.015,M["steel"])
            ball("plunger_knob",(ox+.51,-1.03,1.052),(.037,.036,.027),M["red"])

    elif kind=="can_knockdown":
        box("throwing_backstop",(0,1.22,1.82),(3,.12,1.49),M["darksteel"])
        for ox in (-.77,.77):
            box("can_platform",(ox,.62,1.12),(1.21,.84,.16),M["wood"])
            for row in range(3):
                for j in range(3-row):
                    tin(ox+(j-(2-row)/2)*.187,.50,1.20+row*.194,palette[(row+j)%6])
        tray(0,-.88,1.0,1.16,.35,M["wood"])
        for j in range(6):
            ball("throwing_cork_ball",(-.46+j*.183,-.87,1.095),(.078,)*3,corkmat)

    elif kind=="water_pistol":
        box("water_target_backboard",(0,1.20,1.84),(2.98,.10,1.50),M["blue"])
        for row in range(2):
            for j in range(7):
                x=-1.23+j*.41;z=1.49+row*.49
                ring("water_target_ring",(x,1.12,z),.13,.019,M["yellow"],(math.pi/2,0,0))
                cyl("target_disc",(x,1.13,z),.084,.022,M["red"],24,(math.pi/2,0,0))
                stick("target_pivot",(x,1.1,z+.14),(x,1.1,z+.23),.007,M["steel"])
        for i,x in enumerate((-.95,0,.95)):
            col=palette[i]
            box("toy_water_pistol_body",(x,-.78,1.087),(.31,.12,.13),col,.04)
            stick("water_pistol_barrel",(x+.13,-.78,1.105),(x+.28,-.78,1.105),.029,M["orange"])
            box("pistol_bright_grip",(x-.075,-.77,1.02),(.09,.10,.18),M["yellow"],.025)
            ball("water_reservoir",(x,-.78,1.19),(.13,.062,.067),M["green"])
            line("pistol_safety_tether",[(x,-.73,1.03),(x,-.4,.80),(x,.05,.96)],.008,M["black"])

    elif kind=="cork_target":
        box("target_backstop",(0,1.20,1.80),(3,.12,1.50),M["darksteel"])
        for j in range(3):
            x=-.91+j*.91
            cyl("target_outer",(x,1.10,1.90),.35,.047,M["cream"],48,(math.pi/2,0,0))
            for rr,col,yy in ((.265,M["red"],1.07),(.175,M["cream"],1.045),(.085,M["red"],1.022)):
                cyl("target_concentric_disc",(x,yy,1.90),rr,.013,col,48,(math.pi/2,0,0))
        rifle(-.60,-.82,1.08);rifle(.62,-.82,1.08)
        for j in range(9):
            cyl("cork_pellet",(-1.32+(j%3)*.048,-.87+(j//3)*.05,1.036),.017,.035,corkmat,12)

    elif kind=="senbonbiki":
        for x in (-1.36,1.36):
            box("string_lottery_upright",(x,.71,1.73),(.075,.075,1.57),M["wood"])
        box("string_lottery_header",(0,.71,2.49),(2.80,.10,.14),M["red"])
        for j in range(14):
            x=-1.22+j*.187;endx=-1.18+((j*5)%14)*.18
            line("prize_pull_string",[(x,-.45,1.05),(x,.15,1.98),(x,.66,2.46),(endx,.81,1.41)],.003,M["cream"])
            ball("string_pull_knob",(x,-.45,1.06),(.036,.036,.025),M["red"])
            prize(endx,.82,1.04,.125+rng.random()*.08)
        for j in range(5):
            prize(-1.12+j*.55,1.07,1.84,.30)

    elif kind=="masks":
        for x in (-1.37,1.37):
            box("mask_rack_upright",(x,1.06,1.86),(.05,.06,1.65),M["bamboo"])
        for z in (1.22,1.85,2.48):
            stick("mask_rack_crossbar",(-1.39,1.07,z),(1.39,1.07,z),.022,M["bamboo"])
        for row in range(2):
            for j in range(6):
                x=-1.16+j*.465;y=.94;z=1.50+row*.67
                col=M["white"] if (j+row)%3 else M["cream"]
                ball("original_kitsune_mask_shell",(x,y,z),(.176,.069,.226),col)
                for s in (-1,1):
                    # Hollow-looking pointed ears on the moulded white face.
                    vs=[(x+s*.078,y-.011,z+.15),(x+s*.189,y-.005,z+.155),(x+s*.147,y+.015,z+.346),
                        (x+s*.095,y-.017,z+.178),(x+s*.169,y-.010,z+.178),(x+s*.143,y+.005,z+.290)]
                    mesh("kitsune_pointed_ear",vs[:3],[(0,1,2)],col)
                    mesh("red_inner_ear",vs[3:],[(0,1,2)],M["red"])
                    # Narrow sloping almond eye opening.
                    ex=x+s*.073
                    mesh("mask_almond_eye",[(ex-s*.045,y-.067,z+.035),(ex+s*.046,y-.061,z+.058),
                                            (ex+s*.025,y-.073,z+.013),(ex-s*.036,y-.075,z+.017)],[(0,1,2,3)],M["black"])
                    line("mask_red_cheek_mark",[(x+s*.102,y-.066,z-.012),(x+s*.123,y-.060,z-.056),(x+s*.083,y-.070,z-.088)],.009,M["red"])
                ball("kitsune_raised_muzzle",(x,y-.073,z-.069),(.066,.054,.073),col)
                ball("kitsune_black_nose",(x,y-.119,z-.064),(.022,.011,.017),M["black"])
                line("kitsune_red_mouth",[(x-.037,y-.105,z-.120),(x,y-.119,z-.131),(x+.037,y-.105,z-.120)],.005,M["red"])
                line("mask_hanging_loop",[(x-.04,y,z+.235),(x,y, z+.365),(x+.04,y,z+.235)],.002,M["cream"])

    elif kind=="pinwheel":
        for row in range(2):
            box("pinwheel_wood_display",(0,.27+row*.59,1.01),(2.75,.16,.11),M["wood"])
            for j in range(7):
                x=-1.20+j*.40;y=.27+row*.59;z=1.49+row*.69+(j%2)*.13
                stick("pinwheel_bamboo_stick",(x,y,1.03),(x,y,z+.04),.009,M["bamboo"])
                vs=[];fs=[]
                for q in range(4):
                    a=q*math.pi/2
                    def p(u,v,dep):
                        return (x+u*math.cos(a)-v*math.sin(a),y+dep,z+u*math.sin(a)+v*math.cos(a))
                    k=len(vs)
                    vs.extend([p(0,0,-.028),p(.175,.04,0),p(.154,.184,.008),p(.035,.11,-.09)])
                    fs.extend([(k,k+1,k+2),(k,k+2,k+3)])
                ob=mesh("folded_pinwheel_blades",vs,fs,palette[(j+row)%6])
                for m in palette:
                    ob.data.materials.append(m)
                for f in ob.data.polygons:
                    f.material_index=(f.index//2+j)%6+1
                ball("pinwheel_centre_pin",(x,y-.092,z),(.022,.016,.022),M["yellow"])

    elif kind=="dagashi":
        for row,z in enumerate((1.13,1.66,2.18)):
            box("candy_shelf",(0,1.05,z),(2.92,.48,.058),M["wood"])
            for j in range(8):
                x=-1.27+j*.36
                prize(x,1.0,z+.035,.21)
        for j in range(5):
            x=-1.17+j*.58
            cyl("sweet_jar",(x,-.77,1.18),.19,.37,M["glass"])
            cyl("sweet_jar_lid",(x,-.77,1.38),.20,.041,M["red"])
            for k in range(9):
                a=k*2.399;r=.125*math.sqrt((k+.5)/9)
                ball("jar_hard_candy",(x+r*math.cos(a),-.77+r*math.sin(a),1.035+(k%3)*.094),(.048,.038,.048),palette[(j+k)%6])
            box("handwritten_jar_label",(x,-.963,1.18),(.20,.006,.11),M["cream"],.002)

    elif kind=="toy_sword":
        box("toy_sword_display_back",(0,1.18,1.79),(2.96,.09,1.60),M["darksteel"])
        for row in range(2):
            for j in range(7):
                x=-1.23+j*.40;y=1.04;z=1.30+row*.69
                c=vinyl[(j+row)%6]
                # Inflated, round-ended toy sabre, intentionally bright vinyl.
                stick("inflatable_toy_blade",(x,y,z),(x+.17,y,z+.59),.044,c)
                ball("toy_sword_round_tip",(x+.17,y,z+.59),(.045,)*3,c)
                stick("sword_crossguard",(x-.13,y,z+.035),(x+.13,y,z+.035),.029,M["yellow"])
                stick("sword_grip",(x-.025,y,z-.15),(x,y,z),.027,M["blue"])
                for k in range(4):
                    ring("toy_grip_band",(x-.02+k*.004,y,z-.13+k*.031),.028,.004,M["yellow"])
        for j in range(3):
            ball("toy_ball",(-.80+j*.80,-.77,1.14),(.15,)*3,vinyl[j])

    elif kind=="beanbag":
        # Sloped cornhole-style board adapted to a compact festival counter.
        for ox in (-.75,.75):
            y0,y1=-.25,1.08;z0,z1=1.07,1.69
            vs=[(ox-.59,y0,z0),(ox+.59,y0,z0),(ox+.59,y1,z1),(ox-.59,y1,z1)]
            mesh("beanbag_sloped_board",vs,[(0,1,2,3)],M["wood"])
            for sx in (-1,1):
                stick("beanbag_sideframe",(ox+sx*.60,y0,z0),(ox+sx*.60,y1,z1),.025,M["red"])
            # Three shallow inset target pockets with dark inner bowls.
            for x,y in ((ox,.79),(ox-.29,.28),(ox+.29,.28)):
                z=z0+(y-y0)/(y1-y0)*(z1-z0)
                tilt=math.atan((z1-z0)/(y1-y0))
                cyl("beanbag_target_recess",(x,y,z+.014),.12,.007,M["black"],32,(tilt,0,0))
                ring("beanbag_target_lip",(x,y,z+.024),.125,.015,M["yellow"],(tilt,0,0))
        for j in range(8):
            x=-1.20+(j%4)*.75;y=-.84+(j//4)*.27
            obj=box("soft_cloth_throwing_bag",(x,y,1.016),(.19,.15,.07),palette[j%6],.031)
            obj.rotation_euler[2]=rng.uniform(-.3,.3)
            for yy in (-.061,.061):
                stick("bag_sewn_edge",(x-.076,y+yy,1.05),(x+.076,y+yy,1.05),.0025,M["cream"])

    else:
        raise ValueError("Unknown festival game prop kind: " + kind)

    return {"kind": kind, "objects_created": len(bpy.data.objects) - object_count_before}
