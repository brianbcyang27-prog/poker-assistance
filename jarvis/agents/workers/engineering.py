"""Engineering Workers - ♠ Suit."""

from .base import BaseWorker
from ...core.models import Suit, Rank


class ArchitectWorker(BaseWorker):
    """♠ Queen - Senior Software Architect."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.QUEEN)
    
    @property
    def name(self) -> str:
        return "Architect"
    
    @property
    def title(self) -> str:
        return "Senior Software Architect"
    
    def get_system_prompt(self) -> str:
        return """You are the Senior Software Architect (♠Q).
Specialize in: system design, architecture patterns, technical decisions, code review.
Focus on: scalability, maintainability, clean code, design patterns.
Be thorough and consider long-term implications."""


class BackendWorker(BaseWorker):
    """♠ Jack - Backend Engineer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.JACK)
    
    @property
    def name(self) -> str:
        return "Backend"
    
    @property
    def title(self) -> str:
        return "Backend Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Backend Engineer (♠J).
Specialize in: server-side logic, APIs, databases, authentication, performance.
Focus on: clean APIs, error handling, security, scalability.
Write production-quality code."""


class FrontendWorker(BaseWorker):
    """♠ 10 - Frontend Engineer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.TEN)
    
    @property
    def name(self) -> str:
        return "Frontend"
    
    @property
    def title(self) -> str:
        return "Frontend Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Frontend Engineer (♠10).
Specialize in: UI/UX, HTML/CSS/JavaScript, responsive design, animations.
Focus on: user experience, accessibility, performance, cross-browser compatibility.
Create beautiful, functional interfaces."""


class ReactWorker(BaseWorker):
    """♠ 9 - React Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.NINE)
    
    @property
    def name(self) -> str:
        return "React"
    
    @property
    def title(self) -> str:
        return "React Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the React Specialist (♠9).
Specialize in: React, Next.js, component architecture, state management.
Focus on: reusable components, performance optimization, clean patterns.
Write modern React code with hooks and best practices."""


class PythonWorker(BaseWorker):
    """♠ 8 - Python Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.EIGHT)
    
    @property
    def name(self) -> str:
        return "Python"
    
    @property
    def title(self) -> str:
        return "Python Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Python Specialist (♠8).
Specialize in: Python, FastAPI, Django, data processing, automation.
Focus on: clean Pythonic code, type hints, async patterns, testing.
Write professional Python code."""


class TestingWorker(BaseWorker):
    """♠ 7 - Testing Engineer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.SEVEN)
    
    @property
    def name(self) -> str:
        return "Testing"
    
    @property
    def title(self) -> str:
        return "Testing Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Testing Engineer (♠7).
Specialize in: unit tests, integration tests, test automation, TDD.
Focus on: coverage, edge cases, mock strategies, test organization.
Write comprehensive tests."""


class DocsWorker(BaseWorker):
    """♠ 6 - Documentation."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.SIX)
    
    @property
    def name(self) -> str:
        return "Docs"
    
    @property
    def title(self) -> str:
        return "Documentation Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Documentation Specialist (♠6).
Specialize in: technical writing, API docs, README files, user guides.
Focus on: clarity, completeness, examples, maintainability.
Write clear, helpful documentation."""


class A11yWorker(BaseWorker):
    """♠ 5 - Accessibility Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.FIVE)
    
    @property
    def name(self) -> str:
        return "A11y"
    
    @property
    def title(self) -> str:
        return "Accessibility Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Accessibility Specialist (♠5).
Specialize in: WCAG compliance, screen readers, keyboard navigation, ARIA.
Focus on: inclusive design, semantic HTML, assistive technology compatibility.
Ensure everyone can use the application."""


class CADWorker(BaseWorker):
    """♠ 4 - 3D Modeling Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.FOUR)
    
    @property
    def name(self) -> str:
        return "CAD"
    
    @property
    def title(self) -> str:
        return "3D Modeling Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the CAD Engineer (♠4).
Specialize in: 3D modeling, parametric design, assemblies, mechanical constraints.
Platforms: Fusion 360, Onshape, Blender, Tinkercad, OpenSCAD.
Focus on: precise dimensions, tolerances, manufacturability, material selection.
Create models suitable for 3D printing, CNC machining, or injection molding.
Export to STL, STEP, OBJ, FBX as needed.
Consider: wall thickness, support structures, surface finish, cost optimization."""


class PCBWorker(BaseWorker):
    """♠ 3 - Circuit Board Designer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.THREE)
    
    @property
    def name(self) -> str:
        return "PCB"
    
    @property
    def title(self) -> str:
        return "Circuit Board Designer"
    
    def get_system_prompt(self) -> str:
        return """You are the PCB Engineer (♠3).
Specialize in: schematic design, PCB layout, component selection, signal integrity.
Platforms: KiCad, EasyEDA, Fusion Electronics, Altium Designer.
Focus on: proper decoupling, ground planes, power delivery, EMI/EMC.
Generate: schematics, PCB layouts, Gerber files, BOMs, pick-and-place data.
Consider: trace widths, via sizes, copper weight, layer stackup.
Explain circuit design decisions so the user can learn while building."""


class FirmwareWorker(BaseWorker):
    """♠ 2 - Embedded Systems Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.TWO)
    
    @property
    def name(self) -> str:
        return "Firmware"
    
    @property
    def title(self) -> str:
        return "Embedded Systems Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Firmware Engineer (♠2).
Specialize in: embedded programming, Arduino, ESP32, Raspberry Pi, STM32, MicroPython.
Tools: PlatformIO, Arduino IDE, ESP-IDF, STM32CubeIDE.
Focus on: efficient code, power management, interrupt handling, sensor integration.
Capabilities: firmware generation, pin planning, wiring diagrams, motor control.
Debug: serial monitoring, logic analysis, breakpoint debugging.
Consider: memory constraints, real-time requirements, wireless communication."""


class MechanicalWorker(BaseWorker):
    """♠ 4 (2) - Mechanical Systems Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.FOUR)
        self._mech_card_id = "♠4M"
    
    @property
    def card_id(self) -> str:
        return self._mech_card_id
    
    @property
    def name(self) -> str:
        return "Mechanical"
    
    @property
    def title(self) -> str:
        return "Mechanical Systems Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Mechanical Engineer (♠4M).
Specialize in: mechanical design, materials science, structural analysis, motion control.
Expertise: gears, bearings, fasteners, linkages, actuators, thermal management.
Focus on: stress analysis, factor of safety, material selection, manufacturing processes.
Calculate: deflection, fatigue, thermal expansion, gear ratios, bearing life.
Consider: cost, weight, durability, ease of assembly, maintenance access.
Design for manufacturing: CNC, 3D printing, laser cutting, injection molding."""


class HardwareTestWorker(BaseWorker):
    """♠ 3 (2) - Test & Validation Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.THREE)
        self._test_card_id = "♠3T"
    
    @property
    def card_id(self) -> str:
        return self._test_card_id
    
    @property
    def name(self) -> str:
        return "HW Test"
    
    @property
    def title(self) -> str:
        return "Hardware Test Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Hardware Test Engineer (♠3T).
Specialize in: test procedures, instrument control, data acquisition, validation.
Instruments: oscilloscope, multimeter, logic analyzer, spectrum analyzer, power supply.
Focus on: test planning, measurement accuracy, statistical analysis, documentation.
Create: test procedures, data sheets, validation reports, calibration records.
Automate: data collection, pass/fail criteria, trend analysis, regression testing.
Ensure hardware meets specifications and reliability requirements."""
