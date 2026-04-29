import math
import numpy as np
import bisect

class PPoint:
    def __init__(self, x=0, y=0, z=0):
        self.x=x
        self.y=y
        self.z=z

    def __repr__(self):
        return f"P({self.x},{self.y},{self.z})"

    def __add__(self, other):
        assert isinstance(other, PPoint)
        return PPoint(self.x+other.x,self.y+other.y,self.z+other.z)

    def __sub__(self, other):
        assert isinstance(other, PPoint)
        return PPoint(self.x-other.x,self.y-other.y,self.z-other.z)

    def __mul__(self, s):
        assert type(s) in [float, int]
        return PPoint(self.x*s, self.y*s, self.z*s)

    def __rmul__(self, s):
        assert type(s) in [float, int]
        return PPoint(self.x*s, self.y*s, self.z*s)

    def toH(self):
        x, y, z = self.x, self.y, self.z
        r2 = x * x + y * y + z * z
        assert r2 < 1.0, "Point is outside the Poincaré ball"
        den = 1.0/(1.0 - r2)
        return HPoint(2*x*den, 2*y*den, 2*z*den, (1.0 + r2)*den)

    def length2(self):
        return self.x*self.x+self.y*self.y+self.z*self.z

    def length(self):
        return self.length2()**0.5
    
    def dot(self, other):
        assert isinstance(other, PPoint)
        return self.x*other.x+self.y*other.y+self.z*other.z
    
    def cross(self, other):
        assert isinstance(other, PPoint)
        return PPoint(self.y*other.z - self.z*other.y,
                      self.z*other.x - self.x*other.z,
                      self.x*other.y - self.y*other.x)
    
class HPoint:
    def __init__(self, x=0, y=0, z=0, w=0):
        self.x=x
        self.y=y
        self.z=z
        self.w=w

    def __repr__(self):
        return f"H({self.x},{self.y},{self.z},{self.w})"

    def __add__(self, other):
        assert isinstance(other, HPoint)
        return HPoint(self.x+other.x,self.y+other.y,self.z+other.z,self.w+other.w)

    def __sub__(self, other):
        assert isinstance(other, HPoint)
        return HPoint(self.x-other.x,self.y-other.y,self.z-other.z,self.w-other.w)

    def __mul__(self, s):
        assert type(s) in [float, int]
        return HPoint(self.x*s, self.y*s, self.z*s, self.w*s)

    def __rmul__(self, s):
        assert type(s) in [float, int]
        return HPoint(self.x*s, self.y*s, self.z*s, self.w*s)

    def toP(self):
        x, y, z, w = self.x, self.y, self.z, self.w
        assert w > 0.0, "Point is not on the upper sheet of the hyperboloid"
        sc = 1.0/(w + 1.0)
        return PPoint(x*sc, y*sc, z*sc)

    def dot(self, other):
        assert isinstance(other, HPoint)
        return self.x*other.x+self.y*other.y+self.z*other.z-self.w*other.w

    def norm(self):
        return self.x*self.x+self.y*self.y+self.z*self.z-self.w*self.w

    def euclidean_norm(self):
        return math.sqrt(self.x*self.x+self.y*self.y+self.z*self.z+self.w*self.w)
        
    def lerp(self, other, t):
        assert isinstance(other, HPoint)
        it = 1.0-t
        return HPoint(self.x*it+other.x*t,self.y*it+other.y*t,self.z*it+other.z*t,self.w*it+other.w*t)

    def slerp(self, other, t):
        dot = -self.dot(other)
        if dot < 1.0: dot = 1.0
        theta = math.acosh(dot)
    
        if theta < 1e-9:
            return self
        
        sin_theta = math.sinh(theta)
    
        # Formula Slerp Iperbolica
        a = math.sinh((1 - t) * theta) / sin_theta
        b = math.sinh(t * theta) / sin_theta
    
        return self*a + other*b

    def normalize(self):
        s = abs(self.norm())
        if s > 1.0e-15:
            factor = 1.0/math.sqrt(s)
            self.x*=factor
            self.y*=factor
            self.z*=factor
            self.w*=factor
        return self

    def make_w_positive(self):
        if self.w < 0.0:
            self.x = -self.x
            self.y = -self.y
            self.z = -self.z
            self.w = -self.w
        return self

class HMatrix:
    def __init__(self, mat = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]):
        self.mat = np.array(mat)

    def __mul__(self, other):
        if isinstance(other, HPoint):
            (x,y,z,w) = self.mat.dot([other.x,other.y,other.z,other.w])
            return HPoint(x,y,z,w)
        elif isinstance(other, HMatrix):
            return HMatrix(np.matmul(self.mat, other.mat))
        else:
            assert False, "expected HPoint or HMatrix"

    def inv(self):
        return HMatrix(np.linalg.inv(self.mat))



def HReflection(v:HPoint):
    if isinstance(v, PPoint):
        v = v.toH()
    x, y, z, w = v.x, v.y, v.z, v.w
    
    vec_v = np.array([x, y, z])
    norm_v = np.linalg.norm(vec_v)
    
    if norm_v < 1e-15:
        return np.eye(4)
    
    # Il vettore normale n alla superficie deve essere tale che B(p, n) = 0.
    # Per essere perpendicolare alla retta Op, n deve trovarsi nel piano p-O.
    # Un vettore n = (w * x/norm_v, w * y/norm_v, w * z/norm_v, norm_v)
    # soddisfa B(n, n) = 1 e B(p, n) = 0.
    
    n = np.array([
        w * x / norm_v,
        w * y / norm_v,
        w * z / norm_v,
        norm_v
    ])
    
    # Metrica J
    J = np.diag([1.0, 1.0, 1.0, -1.0])
    
    # Formula di riflessione: R = I - 2 * n * (n^T @ J)
    I = np.eye(4)
    # n_minkowski = n^T @ J = [n_x, n_y, n_z, -n_w]
    n_mink = n @ J
    
    matrix = I - 2.0 * np.outer(n, n_mink)

    return HMatrix(matrix)


def HTranslation(p:HPoint):
    """
    Genera la matrice di traslazione iperbolica (Lorentz Boost) 
    che porta l'origine (0,0,0,1) nel punto p=(xp, yp, zp, wp).
    """
    xp, yp, zp, wp = p.x, p.y, p.z, p.w
    
    # Il fattore comune nelle componenti spaziali è 1 / (wp + 1)
    # wp + 1 non è mai zero perché sull'iperboloide wp >= 1
    f = 1.0 / (wp + 1.0)
    
    return HMatrix([
        [1 + f * xp**2,     f * xp * yp,     f * xp * zp,     xp],
        [f * yp * xp,     1 + f * yp**2,     f * yp * zp,     yp],
        [f * zp * xp,       f * zp * yp,   1 + f * zp**2,     zp],
        [xp,                yp,              zp,              wp]
    ])

def HRotation(p:HPoint, theta:float):
    ax, ay, az = p.x, p.y, p.z
    norm = math.sqrt(ax**2 + ay**2 + az**2)
    assert norm > 1e-10
    
    # Normalizzazione dell'asse
    nx, ny, nz = ax/norm, ay/norm, az/norm
    
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    omc = 1.0 - cos_t # One Minus Cosine
    
    # Formula di Rodrigues per la matrice 3x3
    r00 = cos_t + nx*nx*omc
    r01 = nx*ny*omc - nz*sin_t
    r02 = nx*nz*omc + ny*sin_t
    
    r10 = ny*nx*omc + nz*sin_t
    r11 = cos_t + ny*ny*omc
    r12 = ny*nz*omc - nx*sin_t
    
    r20 = nz*nx*omc - ny*sin_t
    r21 = nz*ny*omc + nx*sin_t
    r22 = cos_t + nz*nz*omc
    
    return HMatrix([
        [r00, r01, r02, 0],
        [r10, r11, r12, 0],
        [r20, r21, r22, 0],
        [0,   0,   0,   1]
    ])



def hslerp(p0, p1, t):
    hp0 = p0.toH().normalize()
    hp1 = p1.toH().normalize()
    return hp0.slerp(hp1, t).make_w_positive().normalize().toP()

def hmidpoint(p0, p1):
    return hslerp(p0, p1, 0.5)

def toface(p:PPoint, R:HMatrix):
    return hmidpoint(p, (R*p.toH()).normalize().toP())

class DodecahedronData:
    def __init__(self, radius: float = 0.9) -> None:
        phi = (1.0 + math.sqrt(5.0)) / 2.0
        inv_phi = 1.0 / phi

        raw_vertices = [
                (-1, -1, -1),
                (-1, -1, 1),
                (-1, 1, -1),
                (-1, 1, 1),
                (1, -1, -1),
                (1, -1, 1),
                (1, 1, -1),
                (1, 1, 1),
                (0, -inv_phi, -phi),
                (0, -inv_phi, phi),
                (0, inv_phi, -phi),
                (0, inv_phi, phi),
                (-inv_phi, -phi, 0),
                (-inv_phi, phi, 0),
                (inv_phi, -phi, 0),
                (inv_phi, phi, 0),
                (-phi, 0, -inv_phi),
                (phi, 0, -inv_phi),
                (-phi, 0, inv_phi),
                (phi, 0, inv_phi),
        ]
        scale = radius / math.sqrt(3)
        self.vertices = [PPoint(*coords)*scale for coords in raw_vertices]

        self.edges = [
            (0, 8),
            (0, 12),
            (0, 16),
            (1, 9),
            (1, 12),
            (1, 18),
            (2, 10),
            (2, 13),
            (2, 16),
            (3, 11),
            (3, 13),
            (3, 18),
            (4, 8),
            (4, 14),
            (4, 17),
            (5, 9),
            (5, 14),
            (5, 19),
            (6, 10),
            (6, 15),
            (6, 17),
            (7, 11),
            (7, 15),
            (7, 19),
            (8, 10),
            (9, 11),
            (12, 14),
            (13, 15),
            (16, 18),
            (17, 19),
        ]

        # Counter-clockwise order when each face is viewed from outside.
        self.faces = [
                [0, 12, 1, 18, 16],
                [0, 16, 2, 10, 8],
                [0, 8, 4, 14, 12],
                [1, 9, 11, 3, 18],
                [1, 12, 14, 5, 9],
                [2, 16, 18, 3, 13],
                [2, 13, 15, 6, 10],
                [3, 11, 7, 15, 13],
                [4, 17, 19, 5, 14],
                [4, 8, 10, 6, 17],
                [5, 19, 7, 11, 9],
                [6, 15, 7, 19, 17],
        ]
        self._computeFaceCenters()
        self._link()

    def _computeFaceCenters(self):
        self.centers = []
        pts = [p.toH() for p in self.vertices]
        for face in self.faces:
            p = sum([pts[i] for i in face], HPoint()) * (1.0/len(face))
            p.normalize()
            self.centers.append(p.toP())

    def _link(self):
        edge_tb = {}
        for edge_i, edge in enumerate(self.edges):
            edge_tb[(edge[0], edge[1])] = edge_i
            edge_tb[(edge[1], edge[0])] = edge_i

        self.edge2faces = {}
        for face_i, face in enumerate(self.faces):
            m = len(face)
            for i in range(m):
                v0 = face[i]
                v1 = face[(i+1)%m]
                edge_i = edge_tb[(v0, v1)]
                if edge_i in self.edge2faces:
                    assert len(self.edge2faces[edge_i]) == 1, "edge belongs to more than 2 faces"
                    self.edge2faces[edge_i].append(face_i)
                else:
                    self.edge2faces[edge_i] = [face_i]

    def uffa(self):
        c = self.centers[0]
        p0 = self.vertices[self.edges[0][0]]
        p1 = self.vertices[self.edges[0][1]]
        edge_midpoint = hmidpoint(p0, p1)

        a = c.length() # distanza centro dod - centro faccia
        r = (1-a**2)/(2*a) # raggio sfera che contiene la faccia
        b = edge_midpoint.length() # distanza centro dod - punto medio spigolo
        c = r + a # distanza centro dod - centro sfera che contiene la faccia

        return math.acos((b**2+r**2-c**2)/(2*b*r))


def compute_magic_number():
    theta = math.pi*135/180
    def f(v): return theta - DodecahedronData(v).uffa() 
    a = 0.5
    b = 0.6
    assert f(a)<0
    assert f(b)>0
    while b-a>1.0e-15:
        c = (a+b)/2
        if f(c)<0: a=c
        else: b=c
    return (a+b)/2


    
dod = DodecahedronData(0.5463956846029262) # WTF??0.5257) # ) # 1.0/phi)

base_matrices = []
for i in range(len(dod.faces)):
    hp = dod.centers[i].toH()
    tr = HTranslation(hp)
    tr = tr*tr
    tr = tr * HRotation(hp, math.pi/5)
    base_matrices.append(tr)
    

def quantize(v, base=10**4):
    return math.floor(v * base + 0.5)

def get_sig(p:HPoint):
    return f"{quantize(p.x),quantize(p.y),quantize(p.z)}"
   
def get_dist(matrix):
    hp = matrix*HPoint(0,0,0,1)
    hp = hp.make_w_positive().normalize()
    x,y,z,w=hp.x,hp.y,hp.z,hp.w
    return math.sqrt(x**2+y**2+z**2+w**2) # n.b. uso la norma euclidea!


def generate_matrices(maxDist = 3):
    global visited, boundaries
    visited = set()
    matrices = []

    def get_info(mat):
        p = (mat * HPoint(0,0,0,1)).make_w_positive().normalize()
        dist = math.sqrt(p.x**2+p.y**2+p.z**2+p.w**2)
        return dist, p, get_sig(p), mat
        
    boundaries = [get_info(HMatrix())]

    def check(info):
        dist, p, sig, mat = info
        if dist > 6.0 and p.y>0 and (p.x**2+p.z**2)/(p.y**2) > 1.0:
            return False
        return p.y >= 0 and dist <= maxDist and sig not in visited
        
    while len(boundaries)>0:
        info = boundaries.pop(0)
        if not check(info): continue
        dist,p,sig,mat = info
        matrices.append(mat)
        visited.add(sig)
        if len(matrices)>100000:
            print("uh oh")
            return matrices

        for m2 in base_matrices:
            mat2 = mat * m2
            child_info = get_info(mat2)
            if check(child_info):
                bisect.insort(boundaries, child_info, key=lambda tup:tup[0])
        
    # print(len(matrices), "matrices")

    return matrices


def make_line_h(hp0, hp1, m):
    return [hp0.lerp(hp1, i / (m - 1)).make_w_positive().normalize().toP() for i in range(m)]

def make_line(p0, p1, m):
    hp0 = p0.toH().normalize()
    hp1 = p1.toH().normalize()
    return make_line_h(hp0, hp1, m)


def make_mesh_data(m=5):
    vertices, faces, face_types = [], [], []
    mrg = 0.10 # 0.05
    mrg2 = 0.18 # 3  0.1
    for (edge_i, edge) in enumerate(dod.edges):
        
        p0 = hslerp(dod.vertices[edge[0]], PPoint(0,0,0), mrg)
        p1 = hslerp(dod.vertices[edge[1]], PPoint(0,0,0), mrg)

        face_pair = dod.edge2faces[edge_i]

        c0 = dod.centers[face_pair[0]]
        c1 = dod.centers[face_pair[1]]  
        if (c1-c0).cross(p0-p1).dot(p0) < 0:            
            c0, c1 = c1, c0
            face_pair = face_pair[::-1]

        refl_l = HReflection(dod.centers[face_pair[0]].toH())
        refl_r = HReflection(dod.centers[face_pair[1]].toH())

        p0_l = hmidpoint(p0, (refl_l * p0.toH()).toP())
        p0_r = hmidpoint(p0, (refl_r * p0.toH()).toP())
        
        p1_l = hmidpoint(p1, (refl_l * p1.toH()).toP())
        p1_r = hmidpoint(p1, (refl_r * p1.toH()).toP())


        for i in range(m+1):
            t = i/m
            k = len(vertices)
            if i < m:
                faces.append((k,k+1,k+5,k+4))
                face_types.append("pillar_a")
                faces.append((k+2,k+3,k+7,k+6))
                face_types.append("pillar_b")
            vertices.append(hslerp(p0_l, p1_l, t))
            p = hslerp(p0, p1, t)
            vertices.append(p)
            vertices.append(p)
            vertices.append(hslerp(p0_r, p1_r, t))

    for (vertex_i, vertex) in enumerate(dod.vertices):
        vf = [i for (i,face) in enumerate(dod.faces) if vertex_i in face]
        assert len(vf) == 3, "vertex does not belong to exactly 3 faces"
        c0 = dod.centers[vf[0]]
        c1 = dod.centers[vf[1]]  
        c2 = dod.centers[vf[2]]
        if c0.cross(c1).dot(c2) < 0:
            c1, c2 = c2, c1
        R0 = HReflection(c0.toH())
        R1 = HReflection(c1.toH())
        R2 = HReflection(c2.toH())
        p000 = vertex
        p111 = hslerp(vertex, PPoint(0,0,0), mrg2) # 0.1
        p011 = toface(p111, R0)
        p101 = toface(p111, R1)
        p110 = toface(p111, R2)

        p001 = hmidpoint(toface(p011, R1), toface(p101, R0))
        p010 = hmidpoint(toface(p011, R2), toface(p110, R0))
        p100 = hmidpoint(toface(p101, R2), toface(p110, R1))

        def add_face(p0, p1, p2, p3):
            k = len(vertices)
            vertices.extend([p0, p1, p2, p3])
            faces.append((k,k+1,k+2,k+3))
            face_types.append("cube")

        add_face(p111, p110, p100, p101)
        add_face(p111, p011, p010, p110)
        add_face(p111, p101, p001, p011)

    return vertices, faces, face_types

 

def foo(n):
    global D
    matrices = generate_matrices(n, maxDist=0.999)
    D = sorted(set([int(get_dist(m)*10**6+0.5) for m in generate_matrices(3)]))
    return len(matrices), len(D)

def get_sig_point(mat):
    hp = mat*HPoint(0,0,0,1)
    assert hp.w>0
    assert abs(hp.norm()+1)<1.0e-8
    return hp.normalize()
        
def get_min_distances(matrices):
    dmin = 1e10
    for i,mat in enumerate(matrices):
        hi = get_sig_point(mat)
        for j in range(i+1,len(matrices)):
            hj = get_sig_point(matrices[j])
            d = (hi-hj).euclidean_norm()
            dmin = min(dmin,d)
    return dmin

def get_next_distances(matrices, prec = 4):
    maxd = 0.0
    for mat in matrices:
        d = get_sig_point(mat).euclidean_norm()
        maxd = max(d,maxd)

    D = set()
    for mat in matrices:
        for m in base_matrices:
            d = get_sig_point(mat*m).euclidean_norm()
            if d>maxd:
                d = int(0.5 + d * 10**prec) * 10**(-prec) 
                D.add(d)
    return sorted(D)


            
