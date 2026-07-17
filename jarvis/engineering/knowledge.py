"""Engineering Knowledge Base — materials, formulas, component databases."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Material:
    """Material properties."""
    name: str
    density: float  # kg/m³
    youngs_modulus: float  # GPa
    yield_strength: float  # MPa
    ultimate_strength: float  # MPa
    thermal_conductivity: float  # W/m·K
    thermal_expansion: float  # 10⁻⁶/°C
    cost_per_kg: float  # USD
    common_uses: list[str] = None
    
    def __post_init__(self):
        if self.common_uses is None:
            self.common_uses = []


@dataclass
class Bearing:
    """Bearing specification."""
    id: str
    type: str  # ball, roller, thrust, needle
    bore: float  # mm
    od: float  # mm
    width: float  # mm
    load_rating: float  # N dynamic
    speed_limit: float  # RPM
    price: float  # USD


@dataclass
class GearRatio:
    """Gear ratio calculation result."""
    ratio: float
    output_rpm: float
    torque_multiplier: float
    efficiency: float
    power_loss: float  # watts


class EngineeringKnowledge:
    """Engineering reference database."""
    
    def __init__(self):
        self.materials = self._init_materials()
        self.bearings = self._init_bearings()
        self.fasteners = self._init_fasteners()
        self.formulas = self._init_formulas()
    
    def _init_materials(self) -> dict[str, Material]:
        return {
            "aluminum_6061": Material(
                name="Aluminum 6061-T6",
                density=2700, youngs_modulus=68.9, yield_strength=276,
                ultimate_strength=310, thermal_conductivity=167,
                thermal_expansion=23.6, cost_per_kg=3.50,
                common_uses=["Structural frames", "Brackets", "Enclosures", "Heat sinks"],
            ),
            "aluminum_7075": Material(
                name="Aluminum 7075-T6",
                density=2810, youngs_modulus=71.7, yield_strength=503,
                ultimate_strength=572, thermal_conductivity=130,
                thermal_expansion=23.6, cost_per_kg=12.00,
                common_uses=["Aerospace", "High-stress parts", "Tooling"],
            ),
            "steel_1018": Material(
                name="Steel 1018 Cold Drawn",
                density=7870, youngs_modulus=205, yield_strength=370,
                ultimate_strength=440, thermal_conductivity=51.9,
                thermal_expansion=11.7, cost_per_kg=0.80,
                common_uses=["Shafts", "Gears", "Fasteners", "General machining"],
            ),
            "steel_304_stainless": Material(
                name="Stainless Steel 304",
                density=8000, youngs_modulus=193, yield_strength=215,
                ultimate_strength=505, thermal_conductivity=16.2,
                thermal_expansion=17.3, cost_per_kg=4.00,
                common_uses=["Food processing", "Medical", "Corrosive environments"],
            ),
            "pla": Material(
                name="PLA (3D Printing)",
                density=1240, youngs_modulus=3.5, yield_strength=60,
                ultimate_strength=50, thermal_conductivity=0.13,
                thermal_expansion=70, cost_per_kg=25.00,
                common_uses=["Prototyping", "Non-functional models", "Low-stress parts"],
            ),
            "abs": Material(
                name="ABS (3D Printing)",
                density=1040, youngs_modulus=2.3, yield_strength=40,
                ultimate_strength=30, thermal_conductivity=0.17,
                thermal_expansion=90, cost_per_kg=22.00,
                common_uses=["Functional prototypes", "Enclosures", "Moving parts"],
            ),
            "petg": Material(
                name="PETG (3D Printing)",
                density=1270, youngs_modulus=2.0, yield_strength=53,
                ultimate_strength=53, thermal_conductivity=0.24,
                thermal_expansion=60, cost_per_kg=30.00,
                common_uses=["Mechanical parts", "Food-safe", "Outdoor"],
            ),
            "carbon_fiber_nylon": Material(
                name="Carbon Fiber Nylon",
                density=1100, youngs_modulus=10.0, yield_strength=80,
                ultimate_strength=90, thermal_conductivity=0.30,
                thermal_expansion=30, cost_per_kg=80.00,
                common_uses=["High-strength lightweight", "Drone frames", "Robotics"],
            ),
            "copper": Material(
                name="Copper C110",
                density=8960, youngs_modulus=117, yield_strength=70,
                ultimate_strength=220, thermal_conductivity=385,
                thermal_expansion=16.9, cost_per_kg=10.00,
                common_uses=["Electrical", "Heat exchangers", "Bus bars"],
            ),
            "brass": Material(
                name="Brass C360",
                density=8500, youngs_modulus=97, yield_strength=125,
                ultimate_strength=340, thermal_conductivity=115,
                thermal_expansion=20.5, cost_per_kg=8.00,
                common_uses=["Fittings", "Gears", "Bushings", "Decorative"],
            ),
        }
    
    def _init_bearings(self) -> list[Bearing]:
        return [
            Bearing("608-2RS", "ball", 8, 22, 7, 3500, 30000, 2.50),
            Bearing("625-2RS", "ball", 5, 16, 5, 1800, 40000, 2.00),
            Bearing("6001-2RS", "ball", 12, 28, 8, 5100, 26000, 3.50),
            Bearing("6002-2RS", "ball", 15, 32, 9, 5600, 24000, 4.00),
            Bearing("6003-2RS", "ball", 17, 35, 10, 6000, 22000, 4.50),
            Bearing("6201-2RS", "ball", 12, 32, 10, 6800, 22000, 4.00),
            Bearing("6202-2RS", "ball", 15, 35, 11, 7800, 20000, 4.50),
            Bearing("6203-2RS", "ball", 17, 40, 12, 9600, 18000, 5.00),
            Bearing("6204-2RS", "ball", 20, 47, 14, 12800, 16000, 6.00),
            Bearing("6205-2RS", "ball", 25, 52, 15, 14000, 14000, 7.00),
            Bearing("6302-2RS", "ball", 15, 42, 13, 11400, 18000, 5.50),
            Bearing("6303-2RS", "ball", 17, 47, 14, 13500, 16000, 6.50),
            Bearing("6304-2RS", "ball", 20, 52, 15, 15900, 14000, 7.50),
            Bearing("685-2RS", "ball", 5, 11, 4, 800, 50000, 1.50),
            Bearing("693-2RS", "ball", 3, 8, 4, 400, 60000, 1.20),
            Bearing("MR105-2RS", "ball", 5, 10, 4, 650, 45000, 1.80),
            Bearing("F695-2RS", "flanged ball", 5, 13, 4, 950, 40000, 2.00),
            Bearing("F623-2RS", "flanged ball", 3, 10, 4, 500, 55000, 1.50),
        ]
    
    def _init_fasteners(self) -> dict:
        return {
            "metric_coarse": {
                "M2": {"pitch": 0.4, "head_d": 3.8, "socket": 1.5},
                "M2.5": {"pitch": 0.45, "head_d": 4.5, "socket": 2.0},
                "M3": {"pitch": 0.5, "head_d": 5.5, "socket": 2.5},
                "M4": {"pitch": 0.7, "head_d": 7.0, "socket": 3.0},
                "M5": {"pitch": 0.8, "head_d": 8.5, "socket": 4.0},
                "M6": {"pitch": 1.0, "head_d": 10.0, "socket": 5.0},
                "M8": {"pitch": 1.25, "head_d": 13.0, "socket": 6.0},
            },
            "imperial": {
                "4-40": {"pitch": 0.635, "head_d": 4.8, "socket": 2.0},
                "6-32": {"pitch": 0.794, "head_d": 5.6, "socket": 2.5},
                "8-32": {"pitch": 0.794, "head_d": 6.4, "socket": 3.0},
                "10-32": {"pitch": 0.794, "head_d": 7.1, "socket": 3.5},
                "1/4-20": {"pitch": 1.27, "head_d": 9.5, "socket": 4.0},
            },
        }
    
    def _init_formulas(self) -> dict:
        return {
            "beam_stress": {
                "name": "Beam Bending Stress",
                "formula": "σ = M*y/I",
                "variables": {
                    "M": "Bending moment (N·m)",
                    "y": "Distance from neutral axis (m)",
                    "I": "Second moment of area (m⁴)",
                },
            },
            "deflection": {
                "name": "Beam Deflection",
                "formula": "δ = F*L³/(3*E*I)",
                "variables": {
                    "F": "Force (N)",
                    "L": "Length (m)",
                    "E": "Young's modulus (Pa)",
                    "I": "Second moment of area (m⁴)",
                },
            },
            "gear_ratio": {
                "name": "Gear Ratio",
                "formula": "GR = N_driven / N_driver",
                "variables": {
                    "N_driven": "Teeth on driven gear",
                    "N_driver": "Teeth on driver gear",
                },
            },
            "torque": {
                "name": "Torque from Force",
                "formula": "τ = F × r",
                "variables": {
                    "F": "Force (N)",
                    "r": "Lever arm (m)",
                },
            },
            "power": {
                "name": "Mechanical Power",
                "formula": "P = τ × ω",
                "variables": {
                    "τ": "Torque (N·m)",
                    "ω": "Angular velocity (rad/s)",
                },
            },
            "bearing_life": {
                "name": "Bearing L10 Life",
                "formula": "L10 = (C/P)³ × 10⁶ rev",
                "variables": {
                    "C": "Dynamic load rating (N)",
                    "P": "Applied load (N)",
                },
            },
            "trace_width": {
                "name": "PCB Trace Width (IPC-2221)",
                "formula": "W = I / (k × ΔT^b)",
                "variables": {
                    "I": "Current (A)",
                    "ΔT": "Temperature rise (°C)",
                    "k": "0.048 (internal) or 0.024 (external)",
                    "b": "0.44",
                },
            },
            "thermal_resistance": {
                "name": "Thermal Resistance",
                "formula": "θ = L/(k*A)",
                "variables": {
                    "L": "Thickness (m)",
                    "k": "Thermal conductivity (W/m·K)",
                    "A": "Cross-sectional area (m²)",
                },
            },
        }
    
    def get_material(self, name: str) -> Optional[dict]:
        """Get material properties."""
        mat = self.materials.get(name)
        if mat:
            return {
                "name": mat.name,
                "density_kg_m3": mat.density,
                "youngs_modulus_gpa": mat.youngs_modulus,
                "yield_strength_mpa": mat.yield_strength,
                "ultimate_strength_mpa": mat.ultimate_strength,
                "thermal_conductivity": mat.thermal_conductivity,
                "thermal_expansion": mat.thermal_expansion,
                "cost_per_kg": mat.cost_per_kg,
                "common_uses": mat.common_uses,
            }
        return None
    
    def list_materials(self) -> list[str]:
        return list(self.materials.keys())
    
    def get_material_recommendation(self, requirements: dict) -> list[str]:
        """Recommend materials based on requirements."""
        candidates = []
        for key, mat in self.materials.items():
            if "min_yield_strength" in requirements:
                if mat.yield_strength < requirements["min_yield_strength"]:
                    continue
            if "max_cost" in requirements:
                if mat.cost_per_kg > requirements["max_cost"]:
                    continue
            if "min_conductivity" in requirements:
                if mat.thermal_conductivity < requirements["min_conductivity"]:
                    continue
            if "application" in requirements:
                if not any(req.lower() in use.lower() for use in mat.common_uses for req in [requirements["application"]]):
                    continue
            candidates.append(key)
        return candidates
    
    def select_bearing(self, load_n: float, speed_rpm: float, bore_mm: float = None) -> Optional[dict]:
        """Select best bearing for given requirements."""
        best = None
        best_score = -1
        
        for b in self.bearings:
            # Check load capacity with safety factor
            if b.load_rating < load_n * 2.5:
                continue
            
            # Check speed limit
            if b.speed_limit < speed_rpm * 1.2:
                continue
            
            # Check bore if specified
            if bore_mm and abs(b.bore - bore_mm) > 1:
                continue
            
            # Score: prefer lower price, higher margin
            score = (b.load_rating / load_n) * (b.speed_limit / speed_rpm) / b.price
            
            if score > best_score:
                best_score = score
                best = b
        
        if best:
            return {
                "id": best.id,
                "type": best.type,
                "bore_mm": best.bore,
                "od_mm": best.od,
                "width_mm": best.width,
                "load_rating_n": best.load_rating,
                "speed_limit_rpm": best.speed_limit,
                "price_usd": best.price,
            }
        return None
    
    def calculate_gear_ratio(self, driver_teeth: int, driven_teeth: int, input_rpm: float) -> dict:
        """Calculate gear ratio and output parameters."""
        ratio = driven_teeth / driver_teeth
        output_rpm = input_rpm / ratio
        efficiency = 0.95 if ratio < 5 else 0.90  # Lower efficiency for higher ratios
        torque_multiplier = ratio * efficiency
        
        return {
            "ratio": round(ratio, 2),
            "output_rpm": round(output_rpm, 1),
            "torque_multiplier": round(torque_multiplier, 2),
            "efficiency": round(efficiency, 2),
            "driver_teeth": driver_teeth,
            "driven_teeth": driven_teeth,
            "input_rpm": input_rpm,
        }
    
    def calculate_beam_stress(self, force_n: float, length_m: float, width_m: float, height_m: float) -> dict:
        """Calculate beam bending stress."""
        import math
        I = (width_m * height_m**3) / 12
        M = force_n * length_m  # Cantilever moment
        y = height_m / 2
        stress_pa = M * y / I
        stress_mpa = stress_pa / 1e6
        
        return {
            "bending_stress_mpa": round(stress_mpa, 2),
            "moment_n_m": round(M, 2),
            "second_moment_m4": I,
            "deflection_factor": round(length_m**3 / (3 * 200e9 * I), 6),  # Steel beam
        }
    
    def query(self, query: str, category: str = None) -> dict:
        """Query the engineering knowledge base."""
        query_lower = query.lower()
        results = {}
        
        # Search materials
        if not category or category == "materials":
            mat_results = []
            for key, mat in self.materials.items():
                if (query_lower in mat.name.lower() or
                    query_lower in key.lower() or
                    any(query_lower in use.lower() for use in mat.common_uses)):
                    mat_results.append({
                        "id": key,
                        "name": mat.name,
                        "uses": mat.common_uses[:3],
                    })
            if mat_results:
                results["materials"] = mat_results
        
        # Search formulas
        if not category or category == "formulas":
            formula_results = []
            for key, formula in self.formulas.items():
                if (query_lower in formula["name"].lower() or
                    query_lower in key.lower()):
                    formula_results.append({
                        "id": key,
                        "name": formula["name"],
                        "formula": formula["formula"],
                    })
            if formula_results:
                results["formulas"] = formula_results
        
        # Search fasteners
        if not category or category == "fasteners":
            fastener_results = []
            for system, sizes in self.fasteners.items():
                for size, info in sizes.items():
                    if query_lower in size.lower():
                        fastener_results.append({
                            "size": size,
                            "system": system,
                            "pitch_mm": info["pitch"],
                        })
            if fastener_results:
                results["fasteners"] = fastener_results
        
        return results if results else {"message": "No results found"}


# Singleton
engineering_knowledge = EngineeringKnowledge()
