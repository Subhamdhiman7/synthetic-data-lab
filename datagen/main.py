import json
import logging
import random
from pathlib import Path
from typing import Optional

import pandas as pd
import questionary
import typer
from pydantic import ValidationError

from .schemas import WizardAnswers, format_target_formula, get_random_row_count



app = typer.Typer(help="Synthetic ML Dataset Generator")
logger = logging.getLogger(__name__)


def setup_logging(outdir: str, level: str = "WARNING"):
    """Setup logging to file and console."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "syntheticgen.log"

    # The CLI can be invoked repeatedly in one process (for example by an
    # embedding application or a test runner). Remove only handlers installed
    # by this function so messages are not duplicated and unrelated handlers
    # remain intact.
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "_syntheticgen_handler", False):
            root_logger.removeHandler(handler)
            handler.close()
    
    # File handler with INFO level for debugging
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler._syntheticgen_handler = True
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler with WARNING level to reduce noise
    console_handler = logging.StreamHandler()
    console_handler._syntheticgen_handler = True
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Root logger setup
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


def _cancel_wizard() -> None:
    """Exit cleanly when the user cancels an interactive prompt."""
    typer.echo("Cancelled.")
    raise typer.Exit(0)


def wizard_interview() -> WizardAnswers:
    """Interactive wizard to collect user requirements."""
    typer.echo("Synthetic ML Dataset Generator")
    typer.echo("Let's create your dataset specification...")
    
    # Size preset
    size = questionary.select(
        "Dataset size?",
        choices=[
            questionary.Choice("Small (~1K rows)", "small"),
            questionary.Choice("Medium (~10K rows)", "medium"),
            questionary.Choice("Large (~100K rows)", "large"),
            questionary.Choice("Very Large (~1M rows)", "very_large")
        ]
    ).ask()
    if size is None:
        _cancel_wizard()
    
    # Dataset description
    description = questionary.text(
        "Describe your dataset (e.g. 'customer churn prediction', 'car fuel efficiency', 'house prices'):",
        validate=lambda x: len(x.strip()) >= 5
    ).ask()
    if description is None:
        _cancel_wizard()
    description = description.strip()
    
    # Auto-detect task type and determine other parameters
    description_lower = description.lower()
    if any(word in description_lower for word in ['churn', 'classification', 'predict whether', 'fraud', 'spam']):
        task = "classification"
    elif any(word in description_lower for word in ['price', 'cost', 'amount', 'efficiency', 'score', 'rating']):
        task = "regression"
    else:
        task = questionary.select(
            "Is this a classification or regression task?",
            choices=[
                questionary.Choice("Classification (predict categories)", "classification"),
                questionary.Choice("Regression (predict numbers)", "regression")
            ]
        ).ask()
        if task is None:
            _cancel_wizard()
    
    # Seed
    seed_input = questionary.text(
        "Random seed (press enter for auto):",
        default=""
    ).ask()
    if seed_input is None:
        _cancel_wizard()

    try:
        seed = int(seed_input) if seed_input.strip() else random.randint(1, 1000000)
    except ValueError:
        typer.echo("Seed must be an integer.")
        raise typer.Exit(1)
    
    return WizardAnswers(
        task=task,
        size=size,
        domain="generic",
        custom_description=description,
        seed=seed
    )


@app.command()
def main(
    size: Optional[str] = typer.Option(None, help="Size preset: small, medium, large, very_large"),
    description: Optional[str] = typer.Option(None, help="Dataset description"),
    task: Optional[str] = typer.Option(None, help="Task type: classification or regression"),
    seed: Optional[int] = typer.Option(None, help="Random seed"),
    plan: Optional[str] = typer.Option(None, help="Path to existing dataset plan JSON file"),
    accept: bool = typer.Option(False, help="Skip confirmation"),
    outdir: str = typer.Option("out", help="Output directory")
):
    """Generate synthetic ML datasets with LLM-assisted specification."""
    
    # Setup logging
    setup_logging(outdir)
    logger.info("Starting synthetic dataset generation")
    
    try:
        # Handle existing plan file
        if plan:
            typer.echo("Loading existing dataset plan...")
            
            # Load plan from file
            try:
                with open(plan, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
            except FileNotFoundError as e:
                raise ValueError(f"Plan file not found: {plan}") from e
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in plan '{plan}' at line {e.lineno}, "
                    f"column {e.colno}: {e.msg}"
                ) from e
            except OSError as e:
                raise ValueError(f"Could not read plan '{plan}': {e}") from e
            
            from .schemas import DatasetPlan
            try:
                dataset_plan = DatasetPlan.model_validate(plan_data)
            except ValidationError as e:
                raise ValueError(f"Invalid dataset plan '{plan}': {e}") from e
            
            # Create minimal answers for generation
            answers = WizardAnswers(
                task=dataset_plan.task,
                size="medium",  # Will be overridden by plan
                domain=dataset_plan.domain,
                custom_description=dataset_plan.description,
                seed=dataset_plan.seed,
                outdir=outdir,
                accept=accept
            )
            
            # Skip to generation step
            typer.echo(f"Loaded plan: {dataset_plan.name}")
            typer.echo(f"   Features: {len(dataset_plan.features)}")
            typer.echo(f"   Target: {dataset_plan.target_name}")
            
        else:
            # Get requirements (wizard or CLI args)
            if not size or not description:
                answers = wizard_interview()
            else:
                # Build from CLI args
                answers = WizardAnswers(
                    task=task or "regression",
                    size=size,
                    domain="generic",
                    custom_description=description,
                    seed=seed or random.randint(1, 1000000),
                    outdir=outdir,
                    accept=accept
                )
            
            logger.info(f"Wizard answers: {answers}")

            if not plan:
                # Generate LLM plan
                typer.echo("\nGenerating dataset specification...")
                from .llm_generator import generate_dataset_plan

                dataset_plan = generate_dataset_plan(answers)

        # Display one consistent summary for loaded and newly generated plans.
        # Prefer the row count stored in the plan.
        if dataset_plan.rows is not None:
            rows = dataset_plan.rows
        else:
            # Backward compatibility for older plans without an explicit row count.
            rows = get_random_row_count(answers.size, answers.seed)

        summary_label = " (from saved plan)" if plan else ""
        typer.echo(f"\nDataset Summary{summary_label}:")
        typer.echo(f"   Task: {answers.task}")
        typer.echo(f"   Size: {answers.size} ({rows:,} rows)")
        typer.echo(f"   Description: {answers.custom_description}")
        typer.echo(f"   Seed: {answers.seed}")

        # Show plan to user (more readable)
        if not plan:  # Only show detailed plan for new generations
            typer.echo(f"\nGenerated Plan:")
            typer.echo(f"   Name: {dataset_plan.name}")
            typer.echo(f"   Description: {dataset_plan.description}")
            typer.echo(f"   Features: {len(dataset_plan.features)}")
            
            # Show all features for approval
            typer.echo(f"   All features:")
            for feature in dataset_plan.features:
                feature_type_label = {"numerical": "NUM", "categorical": "CAT", "binary": "BIN"}.get(feature.type, "DATA")
                missing_info = f" (missing: {feature.missing_rate:.1%})" if getattr(feature, 'missing_rate', 0) > 0 else ""
                typer.echo(f"     [{feature_type_label}] {feature.name}: {feature.domain_semantics}{missing_info}")
            
            typer.echo(f"   Target: {dataset_plan.target_name}")
            typer.echo(f"   Target formula: {format_target_formula(dataset_plan.target_formula)}")
            
            # Ask for dataset name confirmation
            if not accept:
                proposed_name = getattr(dataset_plan, 'dataset_name', dataset_plan.name.lower().replace(' ', '_'))
                dataset_name = questionary.text(
                    f"Dataset filename (without .csv extension):",
                    default=proposed_name,
                    validate=lambda x: len(x.strip()) > 0 and all(c.isalnum() or c in '_-' for c in x.strip())
                ).ask()
                
                # Update the plan with confirmed name
                dataset_plan.dataset_name = dataset_name
            
            # Confirm or regenerate
            if not accept:
                action = questionary.select(
                    "What would you like to do?",
                    choices=[
                        "Accept and generate dataset",
                        "Regenerate plan",
                        "Cancel"
                    ]
                ).ask()
                
                if action == "Cancel":
                    typer.echo("Cancelled.")
                    raise typer.Exit(0)
                elif action == "Regenerate plan":
                    typer.echo("Regenerating...")
                    dataset_plan = generate_dataset_plan(answers)
        
        # Save plan (only for new plans, not existing ones)
        if not plan:
            outdir_path = Path(outdir)
            outdir_path.mkdir(parents=True, exist_ok=True)
            
            # Use dataset name for plan file
            plan_filename = f"{getattr(dataset_plan, 'dataset_name', 'dataset')}_plan.json"
            plan_file = outdir_path / plan_filename
            with open(plan_file, 'w') as f:
                json.dump(dataset_plan.model_dump(), f, indent=2)
            
            typer.echo(f"\nPlan saved to {plan_file}")
        else:
            plan_file = plan
        
        # Generate dataset
        typer.echo("Generating synthetic dataset...")
        from .generator import generate_dataset
        
        answers_dict = answers.model_dump()
        dataset_file, report_file = generate_dataset(str(plan_file), answers_dict, outdir)
        
        # Show preview
        df = pd.read_csv(dataset_file)
        typer.echo(f"\nDataset Preview:")
        typer.echo(f"   Shape: {df.shape}")
        typer.echo(f"   Files: {dataset_file}, {report_file}")
        typer.echo(f"\n{df.head()}")
        
        logger.info("Generation completed successfully")
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
