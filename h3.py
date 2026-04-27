import math
import numpy as np

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

dod = DodecahedronData(0.5464) # WTF??0.5257) # ) # 1.0/phi)

base_matrices = []
for i in range(len(dod.faces)):
    hp = dod.centers[i].toH()
    tr = HTranslation(hp)
    tr = tr*tr
    tr = tr * HRotation(hp, math.pi/5)
    base_matrices.append(tr)
    

def quantize(v):
    return math.floor(v * 10**2 + 0.5)

def get_sig(p:HPoint):
    return f"{quantize(p.x),quantize(p.y),quantize(p.z)}"


def generate_matrices(n=2):
    visited = set()
    matrices = []
    visited.add(get_sig(HPoint(0,0,0,1)))
    matrices.append(HMatrix())
    boundaries = [HMatrix()]

    for shell in range(n):
        boundaries1 = []
        for m2 in boundaries:
            for m1 in base_matrices:
                mat = m2*m1
                sig_p = mat * HPoint(0,0,0,1)
                if sig_p.y <= 0: continue
                pp = sig_p.toP()
                if pp.length() > 0.998: continue
                if shell >=2 and (pp.x**2+pp.z**2)**0.5/pp.y > 0.5: continue
                sig = get_sig(sig_p)
                if sig in visited: continue
                matrices.append(mat)
                boundaries1.append(mat)
                visited.add(sig)
        boundaries = boundaries1
        
    print(len(matrices), "matrices")

    return matrices


def make_line_h(hp0, hp1, m):
    return [hp0.lerp(hp1, i / (m - 1)).make_w_positive().normalize().toP() for i in range(m)]

def make_line(p0, p1, m):
    hp0 = p0.toH().normalize()
    hp1 = p1.toH().normalize()
    return make_line_h(hp0, hp1, m)

def hslerp(p0, p1, t):
    hp0 = p0.toH().normalize()
    hp1 = p1.toH().normalize()
    return hp0.slerp(hp1, t).make_w_positive().normalize().toP()

def hmidpoint(p0, p1):
    return hslerp(p0, p1, 0.5)

def toface(p:PPoint, R:HMatrix):
    return hmidpoint(p, (R*p.toH()).normalize().toP())

def make_mesh_data(m=5):
    vertices, faces = [], []
    for (edge_i, edge) in enumerate(dod.edges):
        
        mrg = 0.05
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
                faces.append((k+2,k+3,k+7,k+6))
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
        p111 = hslerp(vertex, PPoint(0,0,0), 0.1)
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

        add_face(p111, p110, p100, p101)
        add_face(p111, p011, p010, p110)
        add_face(p111, p101, p001, p011)

    return vertices, faces

def make_lines(matrices):
    global lines
    lines = []
    for matrix in matrices:
        for edge in dod.edges:
            hp0 = matrix*dod.vertices[edge[0]].toH()
            hp1 = matrix*dod.vertices[edge[1]].toH()
            
            lines.append(make_line_h(hp0, hp1, 3))

def mahboh():
    matrices = []
    matrices.append(HMatrix())
    matrices.append(base_matrices[0])
    matrices.append(base_matrices[1])
    matrices.append(base_matrices[1] * base_matrices[4])
    make_lines(matrices)


#matrices = [HMatrix()]
#make_lines(matrices)


#matrices = generate_matrices(10)

# matrices = [HMatrix(), base_matrices[0], base_matrices[1]]


# solo per debugging
def apply_matrix_to_point(matrix, p):
    x1,y1,z1=p.x,p.y,p.z
    r2 = (x1**2+y1**2+z1**2)
    den = 1.0/(1-r2)
    x2,y2,z2,w2 = 2*x1*den, 2*y1*den, 2*z1*den, (1+r2)*den
    mat = matrix.mat
    x3 = mat[0,0]*x2+mat[0,1]*y2+mat[0,2]*z2+mat[0,3]*w2
    y3 = mat[1,0]*x2+mat[1,1]*y2+mat[1,2]*z2+mat[1,3]*w2
    z3 = mat[2,0]*x2+mat[2,1]*y2+mat[2,2]*z2+mat[2,3]*w2
    w3 = mat[3,0]*x2+mat[3,1]*y2+mat[3,2]*z2+mat[3,3]*w2
    den = 1/(1+w3)
    x,y,z = x3*den, y3*den, z3*den
    return PPoint(x,y,z)

# solo per debugging
def apply_matrix_to_lines(matrix, lines):
    return [[apply_matrix_to_point(matrix, p) for p in line] for line in lines]


# lines2 = apply_matrix_to_lines(base_matrices[0], lines)

    
    
