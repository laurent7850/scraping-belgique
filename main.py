#!/usr/bin/env python3
"""
Outil de scraping des professions en Belgique.

Récupère les données des professionnels belges à partir de :
- KBO/BCE (Banque-Carrefour des Entreprises)
- Pages d'Or (pagesdor.be)
- CBEAPI.be (API gratuite)

Usage :
    python main.py --profession plombier --ville Bruxelles
    python main.py --profession avocat --province Liège --limit 50
    python main.py --nace 43.221 --ville Namur
    python main.py --list-professions
    python main.py --list-categories
"""

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from nace_codes import find_profession, list_all_professions, NACE_CATEGORIES
from enricher import Enricher
from exporter import export_csv

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def list_categories():
    """Affiche toutes les catégories de professions disponibles."""
    table = Table(title="Catégories de professions disponibles", show_lines=True)
    table.add_column("Catégorie", style="bold cyan")
    table.add_column("Professions", style="white")
    table.add_column("Nb", style="green", justify="right")

    for cat_key, cat_data in NACE_CATEGORIES.items():
        profs = [p["description"] for p in cat_data["professions"].values()]
        table.add_row(
            cat_data["label"],
            ", ".join(profs),
            str(len(profs)),
        )

    console.print(table)


def list_professions_table():
    """Affiche toutes les professions avec leurs codes NACE."""
    table = Table(title="Professions disponibles", show_lines=False)
    table.add_column("Clé", style="cyan")
    table.add_column("Profession", style="white")
    table.add_column("Code NACE", style="green")
    table.add_column("Catégorie", style="yellow")

    for prof in list_all_professions():
        table.add_row(
            prof["key"],
            prof["description"],
            prof["nace"],
            prof["category"],
        )

    console.print(table)


def display_stats(stats: dict, email_stats: dict = None):
    """Affiche les statistiques de scraping."""
    table = Table(title="Résumé du scraping", show_lines=True)
    table.add_column("Métrique", style="bold")
    table.add_column("Valeur", style="green", justify="right")

    table.add_row("Total professionnels", str(stats["total"]))
    table.add_row("Enrichis via Pages d'Or", str(stats["enriched_pagesdor"]))
    table.add_row("Enrichis via CBEAPI", str(stats["enriched_cbeapi"]))
    if stats.get("enriched_email", 0) > 0:
        table.add_row("Enrichis via email approfondi", str(stats["enriched_email"]))
    table.add_row("Avec téléphone", str(stats["with_phone"]))
    table.add_row("Avec email", str(stats["with_email"]))
    table.add_row("Avec site web", str(stats["with_website"]))

    if stats["total"] > 0:
        pct_phone = (stats["with_phone"] / stats["total"]) * 100
        pct_email = (stats["with_email"] / stats["total"]) * 100
        table.add_row("% avec téléphone", f"{pct_phone:.1f}%")
        table.add_row("% avec email", f"{pct_email:.1f}%")

    console.print(table)

    # Détails enrichissement email si disponibles
    if email_stats and email_stats.get("total_processed", 0) > 0:
        email_table = Table(title="Détails enrichissement email", show_lines=True)
        email_table.add_column("Source", style="bold")
        email_table.add_column("Emails trouvés", style="green", justify="right")

        email_table.add_row("Pages d'Or (détail)", str(email_stats.get("email_found_pagesdor", 0)))
        email_table.add_row("Site web entreprise", str(email_stats.get("email_found_website", 0)))
        email_table.add_row("Google Search", str(email_stats.get("email_found_google", 0)))
        email_table.add_row("Non trouvés", str(email_stats.get("email_not_found", 0)))

        console.print(email_table)


def run_scraping(args):
    """Lance le scraping selon les arguments."""
    # Résoudre la profession
    keyword = ""
    pagesdor_keyword = ""
    nace_code = args.nace or ""
    profession_name = ""

    if args.profession:
        matches = find_profession(args.profession)
        if not matches:
            console.print(f"[red]Profession '{args.profession}' non trouvée dans le dictionnaire.[/red]")
            console.print("[yellow]Recherche directe avec ce mot-clé...[/yellow]")
            keyword = args.profession
            profession_name = args.profession
        elif len(matches) == 1:
            match = matches[0]
            keyword = match["description"]
            pagesdor_keyword = match["pagesdor_keyword"]
            nace_code = nace_code or match["nace"]
            profession_name = match["description"]
            console.print(
                f"[green]Profession trouvée :[/green] {match['description']} "
                f"(NACE: {match['nace']}, Catégorie: {match['category']})"
            )
        else:
            console.print(f"[yellow]Plusieurs professions correspondent à '{args.profession}' :[/yellow]")
            for i, m in enumerate(matches, 1):
                console.print(f"  {i}. {m['description']} (NACE: {m['nace']})")

            choice = console.input("[bold]Choisissez un numéro (ou Entrée pour le premier) : [/bold]")
            idx = int(choice) - 1 if choice.strip().isdigit() else 0
            idx = max(0, min(idx, len(matches) - 1))

            match = matches[idx]
            keyword = match["description"]
            pagesdor_keyword = match["pagesdor_keyword"]
            nace_code = nace_code or match["nace"]
            profession_name = match["description"]
    elif nace_code:
        keyword = nace_code
        profession_name = nace_code

    if not keyword and not nace_code:
        console.print("[red]Veuillez spécifier --profession ou --nace[/red]")
        sys.exit(1)

    # Localisation
    location = args.ville or args.province or ""

    # Afficher le récapitulatif
    deep_label = "Oui (+ email approfondi)" if args.deep_enrich else ("Oui" if args.enrich else "Non")
    console.print(Panel(
        f"[bold]Profession :[/bold] {profession_name}\n"
        f"[bold]Code NACE :[/bold] {nace_code or 'N/A'}\n"
        f"[bold]Localisation :[/bold] {location or 'Toute la Belgique'}\n"
        f"[bold]Max résultats :[/bold] {args.limit}\n"
        f"[bold]Enrichissement :[/bold] {deep_label}",
        title="Configuration du scraping",
        border_style="blue",
    ))

    # Lancer le scraping
    enricher = Enricher(
        use_pagesdor=args.enrich,
        use_cbeapi=args.enrich,
        use_deep_email=args.deep_enrich,
    )

    try:
        professionals = enricher.search_and_enrich(
            keyword=keyword,
            pagesdor_keyword=pagesdor_keyword,
            nace_code=nace_code,
            location=location,
            max_results=args.limit,
        )

        if not professionals:
            console.print("[yellow]Aucun résultat trouvé.[/yellow]")
            return

        # Ajouter le nom de profession
        for prof in professionals:
            if not prof.profession:
                prof.profession = profession_name

        # Exporter
        output_path = export_csv(
            professionals,
            profession_name=profession_name,
            location=location,
            output_path=args.output or "",
        )

        # Afficher les stats
        display_stats(enricher.get_stats(), enricher.get_email_stats())

        if output_path:
            console.print(f"\n[bold green]Fichier CSV exporté :[/bold green] {output_path}")

    finally:
        enricher.close()


def main():
    parser = argparse.ArgumentParser(
        description="Scraping des professions en Belgique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python main.py --profession plombier --ville Bruxelles
  python main.py --profession avocat --province Liège --limit 50
  python main.py --nace 43.221 --ville Namur
  python main.py --profession dentiste --no-enrich
  python main.py --profession plombier --ville Bruxelles --deep-enrich
  python main.py --list-professions
  python main.py --list-categories
        """,
    )

    # Mode liste
    parser.add_argument(
        "--list-professions",
        action="store_true",
        help="Affiche toutes les professions disponibles",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="Affiche les catégories de professions",
    )

    # Recherche
    parser.add_argument(
        "--profession", "-p",
        type=str,
        help="Nom de la profession (ex: plombier, avocat, dentiste)",
    )
    parser.add_argument(
        "--nace", "-n",
        type=str,
        help="Code NACE direct (ex: 43.221)",
    )

    # Localisation
    parser.add_argument(
        "--ville", "-v",
        type=str,
        help="Ville ou code postal",
    )
    parser.add_argument(
        "--province",
        type=str,
        help="Province belge",
    )

    # Options
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=100,
        help="Nombre max de résultats (défaut: 100)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Désactiver l'enrichissement Pages d'Or / CBEAPI",
    )
    parser.add_argument(
        "--deep-enrich",
        action="store_true",
        help="Enrichissement email approfondi (Pages d'Or détail + site web + Google)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Chemin du fichier CSV de sortie",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbeux (debug)",
    )

    args = parser.parse_args()
    args.enrich = not args.no_enrich
    if not hasattr(args, "deep_enrich"):
        args.deep_enrich = False

    setup_logging(args.verbose)

    # Bannière
    console.print(Panel(
        Text("Scraping Professions Belgique", style="bold white"),
        subtitle="KBO + Pages d'Or + CBEAPI",
        border_style="bright_blue",
    ))

    if args.list_categories:
        list_categories()
    elif args.list_professions:
        list_professions_table()
    elif args.profession or args.nace:
        run_scraping(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
