"""M3 compiler: persona packages -> optimized DSPy programs (PRD 10).

The compile stage turns the package's files plus train traces into a DSPy
program whose predictor instructions are optimized (GEPA) against the same
judge the M2 harness uses. Test traces are never visible to compilation.
"""

from .compile import CompileResult, run_compile
from .data import build_datasets, trace_to_example
from .metric import make_feedback_metric
from .program import PersonaProgram, persona_brief, seed_instructions
from .runtime import generate_compiled, load_compiled

__all__ = [
    "CompileResult",
    "PersonaProgram",
    "build_datasets",
    "generate_compiled",
    "load_compiled",
    "make_feedback_metric",
    "persona_brief",
    "run_compile",
    "seed_instructions",
    "trace_to_example",
]
