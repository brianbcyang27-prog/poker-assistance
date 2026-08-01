"""Education domain — learning and teaching (new in v10)."""

from .base import DomainMaster, DomainWorker
from .models import Domain


class TutorWorker(DomainWorker):
    """One-on-one tutoring adapted to the learner's level."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Education Tutor. Teach one concept at a time, adapt to the "
            "learner's level, use concrete examples, and check understanding before "
            "moving on. Never assume prior knowledge."
        )


class CurriculumWorker(DomainWorker):
    """Structured learning paths and lesson plans."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Curriculum Designer. Produce structured, sequenced learning "
            "paths with clear objectives, prerequisites, milestones, and assessment "
            "checkpoints. Align to standard learning taxonomies."
        )


class AssessmentWorker(DomainWorker):
    """Quizzes, exercises, and progress evaluation."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Assessment Specialist. Design quizzes and exercises that "
            "measure the stated learning objectives, provide rubrics, and give "
            "actionable feedback on learner answers."
        )


class ExplainerWorker(DomainWorker):
    """Clear, intuitive explanations of complex ideas."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Explainer. Break complex ideas into intuitive, memorable "
            "explanations. Prefer analogies and mental models over jargon; include a "
            "concrete example with every explanation."
        )


class EducationMaster(DomainMaster):
    """Education domain master — head of learning and teaching."""

    def __init__(self):
        super().__init__(Domain.EDUCATION, "education.master")

    @property
    def name(self) -> str:
        return "Education Master"

    @property
    def title(self) -> str:
        return "Head of Learning & Teaching"

    def _build_members(self) -> None:
        self.register_member(TutorWorker(Domain.EDUCATION, "education.tutor"))
        self.register_member(CurriculumWorker(Domain.EDUCATION, "education.curriculum"))
        self.register_member(AssessmentWorker(Domain.EDUCATION, "education.assessment"))
        self.register_member(ExplainerWorker(Domain.EDUCATION, "education.explainer"))
