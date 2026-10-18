#!/usr/bin/env python
"""
Seed the Category table with default civic complaint categories.
Run: python manage.py shell < scripts/seed_categories.py
OR:  python scripts/seed_categories.py  (with DJANGO_SETTINGS_MODULE set)
"""
import os
import sys
import django

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

from apps.complaints.models import Category

CATEGORIES = [
    {"name": "Roads & Potholes",      "slug": "roads-potholes",     "icon": "🚧", "default_sla_days": 7,  "sort_order": 1},
    {"name": "Water Supply",           "slug": "water-supply",       "icon": "💧", "default_sla_days": 3,  "sort_order": 2},
    {"name": "Sanitation & Waste",     "slug": "sanitation-waste",   "icon": "🗑️", "default_sla_days": 2,  "sort_order": 3},
    {"name": "Electricity",            "slug": "electricity",        "icon": "⚡", "default_sla_days": 2,  "sort_order": 4},
    {"name": "Parks & Gardens",        "slug": "parks-gardens",      "icon": "🌳", "default_sla_days": 14, "sort_order": 5},
    {"name": "Public Safety",          "slug": "public-safety",      "icon": "🚨", "default_sla_days": 1,  "sort_order": 6},
    {"name": "Noise Pollution",        "slug": "noise-pollution",    "icon": "🔊", "default_sla_days": 3,  "sort_order": 7},
    {"name": "Drainage & Flooding",    "slug": "drainage-flooding",  "icon": "🌊", "default_sla_days": 3,  "sort_order": 8},
    {"name": "Stray Animals",          "slug": "stray-animals",      "icon": "🐕", "default_sla_days": 5,  "sort_order": 9},
    {"name": "Other",                  "slug": "other",              "icon": "📋", "default_sla_days": 7,  "sort_order": 10},
    {"name": "Education",              "slug": "education",          "icon": "🎓", "default_sla_days": 7,  "sort_order": 11},
]

created = 0
updated = 0
for data in CATEGORIES:
    obj, is_new = Category.objects.update_or_create(
        slug=data["slug"],
        defaults={k: v for k, v in data.items() if k != "slug"},
    )
    if is_new:
        created += 1
        print(f"  Created: {obj.name}")
    else:
        updated += 1
        print(f"  Updated: {obj.name}")

print(f"\nDone. Created: {created}, Updated: {updated}")
