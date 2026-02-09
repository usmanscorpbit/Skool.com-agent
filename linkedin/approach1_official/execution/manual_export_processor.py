"""
Manual Export Processor
Processes LinkedIn data exports (connections, Sales Navigator, etc.)
"""

import csv
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.types import LinkedInProfile, ApproachType, ConnectionDegree

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / ".tmp" / "approach1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ManualExportProcessor:
    """
    Processes manually exported data from LinkedIn.

    Supported export types:
    - LinkedIn Connections export (CSV)
    - Sales Navigator lead list export (CSV)
    - Custom CSV with profile URLs
    """

    @staticmethod
    def process_connections_export(filepath: Path) -> List[LinkedInProfile]:
        """
        Process LinkedIn Connections export.

        LinkedIn allows you to export your connections at:
        Settings > Data Privacy > Get a copy of your data > Connections

        Args:
            filepath: Path to Connections.csv

        Returns:
            List of LinkedInProfile objects
        """
        profiles = []

        with open(filepath, encoding='utf-8') as f:
            # Skip header rows (LinkedIn exports have metadata rows)
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # LinkedIn connection export fields:
                    # First Name, Last Name, Email Address, Company, Position, Connected On
                    profile = LinkedInProfile(
                        id=f"conn_{hash(row.get('Email Address', '') + row.get('First Name', ''))}",
                        name=f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                        headline=f"{row.get('Position', '')} at {row.get('Company', '')}".strip(' at'),
                        profile_url="",  # Not included in export
                        company=row.get('Company', ''),
                        title=row.get('Position', ''),
                        connection_degree=ConnectionDegree.FIRST,  # These are all 1st degree
                        source_approach=ApproachType.OFFICIAL_API,
                        scraped_at=datetime.now()
                    )

                    if profile.name:
                        profiles.append(profile)

                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue

        return profiles

    @staticmethod
    def process_sales_navigator_export(filepath: Path) -> List[LinkedInProfile]:
        """
        Process Sales Navigator lead list export.

        Args:
            filepath: Path to exported CSV

        Returns:
            List of LinkedInProfile objects
        """
        profiles = []

        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Sales Navigator export fields vary but typically include:
                    # First Name, Last Name, Title, Company, Location, LinkedIn Profile URL
                    profile = LinkedInProfile(
                        id=ManualExportProcessor._extract_profile_id(
                            row.get('LinkedIn Profile URL', row.get('Profile URL', ''))
                        ),
                        name=f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                        headline=row.get('Title', ''),
                        profile_url=row.get('LinkedIn Profile URL', row.get('Profile URL', '')),
                        location=row.get('Location', row.get('Geography', '')),
                        company=row.get('Company', row.get('Current Company', '')),
                        title=row.get('Title', row.get('Current Title', '')),
                        industry=row.get('Industry', ''),
                        connection_degree=ManualExportProcessor._parse_degree(
                            row.get('Degree', row.get('Connection Degree', ''))
                        ),
                        source_approach=ApproachType.OFFICIAL_API,
                        scraped_at=datetime.now()
                    )

                    if profile.name:
                        profiles.append(profile)

                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue

        return profiles

    @staticmethod
    def process_custom_csv(
        filepath: Path,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> List[LinkedInProfile]:
        """
        Process a custom CSV file with profile data.

        Args:
            filepath: Path to CSV file
            column_mapping: Map of CSV columns to profile fields
                Example: {"Name": "name", "Job Title": "title", "URL": "profile_url"}

        Returns:
            List of LinkedInProfile objects
        """
        # Default column mapping
        default_mapping = {
            "name": ["name", "full_name", "fullname", "Name", "Full Name"],
            "headline": ["headline", "title", "job_title", "Headline", "Title"],
            "profile_url": ["profile_url", "url", "linkedin_url", "Profile URL", "LinkedIn URL"],
            "location": ["location", "city", "Location", "City"],
            "company": ["company", "current_company", "Company", "Current Company"],
            "title": ["title", "job_title", "position", "Title", "Position"],
            "industry": ["industry", "Industry"],
        }

        profiles = []

        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            # Build mapping from CSV columns to profile fields
            field_map = {}
            for field, possible_names in default_mapping.items():
                for name in possible_names:
                    if name in headers:
                        field_map[field] = name
                        break

            # Override with custom mapping if provided
            if column_mapping:
                for csv_col, profile_field in column_mapping.items():
                    if csv_col in headers:
                        field_map[profile_field] = csv_col

            for row in reader:
                try:
                    profile = LinkedInProfile(
                        id=ManualExportProcessor._extract_profile_id(
                            row.get(field_map.get("profile_url", ""), "")
                        ) or str(hash(row.get(field_map.get("name", ""), ""))),
                        name=row.get(field_map.get("name", ""), ""),
                        headline=row.get(field_map.get("headline", ""), ""),
                        profile_url=row.get(field_map.get("profile_url", ""), ""),
                        location=row.get(field_map.get("location", ""), ""),
                        company=row.get(field_map.get("company", ""), ""),
                        title=row.get(field_map.get("title", ""), ""),
                        industry=row.get(field_map.get("industry", ""), ""),
                        source_approach=ApproachType.OFFICIAL_API,
                        scraped_at=datetime.now()
                    )

                    if profile.name:
                        profiles.append(profile)

                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue

        return profiles

    @staticmethod
    def process_url_list(filepath: Path) -> List[Dict]:
        """
        Process a simple list of LinkedIn profile URLs.

        Args:
            filepath: Path to text file with one URL per line

        Returns:
            List of dicts with profile URLs for scraping
        """
        urls = []

        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and "linkedin.com/in/" in line:
                    urls.append({
                        "profile_url": line,
                        "profile_id": ManualExportProcessor._extract_profile_id(line)
                    })

        return urls

    @staticmethod
    def _extract_profile_id(url: str) -> str:
        """Extract profile ID from URL"""
        import re
        if not url:
            return str(hash(url))
        match = re.search(r'/in/([^/?\s]+)', url)
        return match.group(1) if match else str(hash(url))

    @staticmethod
    def _parse_degree(value: str) -> ConnectionDegree:
        """Parse connection degree"""
        value = str(value).lower()
        if "1" in value or "first" in value:
            return ConnectionDegree.FIRST
        if "2" in value or "second" in value:
            return ConnectionDegree.SECOND
        if "3" in value or "third" in value:
            return ConnectionDegree.THIRD
        return ConnectionDegree.OUT_OF_NETWORK


def process_export(
    filepath: str,
    export_type: str = "auto"
) -> List[LinkedInProfile]:
    """
    Main entry point for processing exports.

    Args:
        filepath: Path to export file
        export_type: "connections", "sales_navigator", "custom", or "auto"

    Returns:
        List of LinkedInProfile objects
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    processor = ManualExportProcessor()

    # Auto-detect export type
    if export_type == "auto":
        with open(path, encoding='utf-8') as f:
            first_line = f.readline().lower()
            if "first name" in first_line and "connected on" in first_line:
                export_type = "connections"
            elif "sales navigator" in first_line or "lead" in first_line:
                export_type = "sales_navigator"
            else:
                export_type = "custom"

    if export_type == "connections":
        profiles = processor.process_connections_export(path)
    elif export_type == "sales_navigator":
        profiles = processor.process_sales_navigator_export(path)
    else:
        profiles = processor.process_custom_csv(path)

    # Save processed profiles
    output_file = OUTPUT_DIR / "processed_profiles.json"
    with open(output_file, "w") as f:
        json.dump([p.to_dict() for p in profiles], f, indent=2)
    print(f"Saved {len(profiles)} profiles to {output_file}")

    return profiles


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python manual_export_processor.py <csv_file> [export_type]")
        print("Export types: connections, sales_navigator, custom, auto (default)")
        sys.exit(1)

    filepath = sys.argv[1]
    export_type = sys.argv[2] if len(sys.argv) > 2 else "auto"

    print(f"Processing: {filepath}")
    print(f"Export type: {export_type}")

    profiles = process_export(filepath, export_type)

    print(f"\nProcessed {len(profiles)} profiles:")
    for p in profiles[:5]:
        print(f"  - {p.name}: {p.headline}")
    if len(profiles) > 5:
        print(f"  ... and {len(profiles) - 5} more")
