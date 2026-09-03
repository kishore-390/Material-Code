"""
Realistic seed data (spec section 33).

Run with:  docker compose exec backend python -m app.seed

Creates CPSEs, roles, demo users, 100+ industrial materials organized
into duplicate groups (so the AI has real matches to find) plus
standalone unique items, then runs every material through the *real*
AI analysis pipeline (embeddings -> pgvector search -> scoring ->
decision engine) so dashboard numbers, approvals and common codes are
all genuine, not hardcoded.
"""
import logging

from app.ai.analyzer import analyze_material, ensure_embeddings
from app.core.security import hash_password
from app.db.base import Base  # noqa: F401 - ensures all models are registered
from app.db.session import SessionLocal, engine
from app.models.cpse import CPSEOrganization
from app.models.material import Material, MaterialAttribute
from app.models.user import Role, User
from app.services import normalization
from app.services.code_generator import ensure_sequence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

ROLES = [
    ("ADMIN", "Full system administration, thresholds and audit access"),
    ("MATERIAL_EXPERT", "Reviews AI recommendations and approves/rejects harmonization"),
    ("CPSE_USER", "Uploads and searches materials for their own CPSE"),
    ("VIEWER", "Read-only dashboards and reports"),
]

CPSES = [
    ("IOCL", "Indian Oil Corporation Limited", "Oil & Gas"),
    ("ONGC", "Oil and Natural Gas Corporation", "Oil & Gas"),
    ("BPCL", "Bharat Petroleum Corporation Limited", "Oil & Gas"),
    ("HPCL", "Hindustan Petroleum Corporation Limited", "Oil & Gas"),
    ("GAIL", "GAIL (India) Limited", "Gas"),
    ("BHEL", "Bharat Heavy Electricals Limited", "Heavy Engineering"),
    ("NTPC", "NTPC Limited", "Power"),
    ("SAIL", "Steel Authority of India Limited", "Steel"),
    ("HAL", "Hindustan Aeronautics Limited", "Aerospace & Defence"),
    ("BEL", "Bharat Electronics Limited", "Electronics & Defence"),
]

USERS = [
    # username, email, full_name, password, role, cpse_code
    ("admin", "admin@material.gov.in", "System Administrator", "Admin@123", "ADMIN", None),
    ("raj.kumar", "raj.kumar@material.gov.in", "Raj Kumar", "Expert@123", "MATERIAL_EXPERT", None),
    ("priya.sharma", "priya.sharma@material.gov.in", "Priya Sharma", "Expert@123", "MATERIAL_EXPERT", None),
    ("iocl.user", "user@iocl.co.in", "Amit Verma", "Cpse@123", "CPSE_USER", "IOCL"),
    ("ongc.user", "user@ongc.co.in", "Sunita Rao", "Cpse@123", "CPSE_USER", "ONGC"),
    ("bpcl.user", "user@bpcl.co.in", "Manoj Nair", "Cpse@123", "CPSE_USER", "BPCL"),
    ("hpcl.user", "user@hpcl.co.in", "Kavita Iyer", "Cpse@123", "CPSE_USER", "HPCL"),
    ("sail.user", "user@sail.co.in", "Deepak Singh", "Cpse@123", "CPSE_USER", "SAIL"),
    ("viewer", "viewer@material.gov.in", "Audit Viewer", "Viewer@123", "VIEWER", None),
]

# Each group represents the *same physical material* described differently by 2-4 CPSEs.
DUPLICATE_GROUPS = [
    {
        "category": "Pipes", "material_type": "Carbon Steel", "attrs": {"Schedule": "SCH 40"},
        "variants": [
            ("IOCL", "IOCL-PIP-1023", "Carbon Steel Seamless Pipe", "ASTM A106 Grade B, 4 inch", "Meter", "Jindal Saw", "JSL"),
            ("ONGC", "ONGC-4481", "Seamless Carbon Steel Pipe", 'ASTM A106 Gr.B, 4"', "Meter", "Jindal Saw", "JSL"),
            ("BPCL", "BPCL-CS-0912", "Carbon Steel Seamless Pipe", "A106 Grade B", "M", "Tata Steel", "Tata"),
            ("HPCL", "HPCL-P-7821", "CS Seamless Pipe 4 in", "ASTM A106 GR B DN100", "Meter", "ISMT", "ISMT"),
        ],
    },
    {
        "category": "Valves", "material_type": "Cast Steel", "attrs": {"End Connection": "Flanged"},
        "variants": [
            ("IOCL", "IOCL-VLV-2011", "Gate Valve Cast Steel", "ASTM A216 WCB, 6 inch, Class 300", "Nos", "L&T Valves", "Leader"),
            ("ONGC", "ONGC-6612", "Cast Steel Gate Valve", "A216 WCB, 6\", Class 300", "Numbers", "L&T Valves", "Leader"),
            ("GAIL", "GAIL-GTV-0087", "Gate Valve, Cast Steel Body", "ASTM A216 Gr.WCB 6IN CL300", "NOS", "Audco", "Audco"),
        ],
    },
    {
        "category": "Bearings", "material_type": "Steel", "attrs": {"Type": "Deep Groove Ball"},
        "variants": [
            ("BHEL", "BHEL-BRG-3301", "Deep Groove Ball Bearing", "SKF 6205-2RS, 25x52x15mm", "Nos", "SKF", "SKF"),
            ("NTPC", "NTPC-BRG-441", "Ball Bearing Deep Groove", "6205 2RS 25x52x15 mm", "Numbers", "SKF", "SKF"),
            ("SAIL", "SAIL-BR-9021", "DGBB 6205", "6205-2RS, 25X52X15", "EA", "FAG", "FAG"),
        ],
    },
    {
        "category": "Lubricants", "material_type": "Industrial", "attrs": {"Viscosity Grade": "ISO VG 68"},
        "variants": [
            ("NTPC", "NTPC-LUB-5510", "Industrial Gear Oil ISO VG 68", "IS 8406, ISO VG 68", "Liter", "Indian Oil", "Servo"),
            ("BHEL", "BHEL-LUB-220", "Ind. Gear Lubricant VG68", "IS:8406 VG-68", "Litre", "Indian Oil", "Servo"),
            ("SAIL", "SAIL-LB-6673", "Gear Oil VG 68 Industrial", "ISO VG68", "L", "Bharat Petroleum", "MAK"),
        ],
    },
    {
        "category": "Flanges", "material_type": "Stainless Steel", "attrs": {"Rating": "150#"},
        "variants": [
            ("IOCL", "IOCL-FLG-4471", "Stainless Steel Weld Neck Flange", "ASTM A182 F304, 4 inch, 150#", "Nos", "MSL", "MSL"),
            ("BPCL", "BPCL-SS-3390", "SS Weld Neck Flange 4in 150#", "A182 F304 4\" CLASS 150", "Numbers", "MSL", "MSL"),
            ("HPCL", "HPCL-FL-8823", "Weld Neck Flange, Stainless Steel", "ASTM A182 Gr.F304 DN100 150#", "NOS", "Metline", "Metline"),
        ],
    },
    {
        "category": "Motors", "material_type": "Induction", "attrs": {"Power": "15 kW"},
        "variants": [
            ("BHEL", "BHEL-MTR-1120", "3-Phase Induction Motor 15kW", "IE3, 415V, 1440 RPM, 15 kW", "Nos", "BHEL", "BHEL"),
            ("NTPC", "NTPC-MOT-903", "Induction Motor 15 KW 3 Phase", "IE3 415V 1440RPM 15KW", "Numbers", "BHEL", "BHEL"),
        ],
    },
    {
        "category": "Pumps", "material_type": "Centrifugal", "attrs": {"Head": "40m"},
        "variants": [
            ("IOCL", "IOCL-PMP-6602", "Centrifugal Pump, 40m Head", "API 610, 100x80-315, 40m Head", "Nos", "Kirloskar", "KBL"),
            ("ONGC", "ONGC-9911", "Centrifugal Water Pump 40 m Head", "API610 100X80 315 40MTR", "Numbers", "Kirloskar", "KBL"),
        ],
    },
    {
        "category": "Cables", "material_type": "Copper", "attrs": {"Size": "3.5C x 240 sqmm"},
        "variants": [
            ("NTPC", "NTPC-CBL-770", "XLPE Copper Power Cable 3.5Cx240sqmm", "IS 7098, 3.5Cx240 sq.mm, 1.1kV", "Meter", "Polycab", "Polycab"),
            ("BHEL", "BHEL-CB-2210", "Copper XLPE Cable 3.5C x 240 sqmm", "IS:7098 1.1KV 3.5CX240SQMM", "Mtr", "Havells", "Havells"),
        ],
    },
    {
        "category": "Transformers", "material_type": "Distribution", "attrs": {"Rating": "1000 kVA"},
        "variants": [
            ("NTPC", "NTPC-TRF-330", "Distribution Transformer 1000kVA", "IS 2026, 11kV/433V, 1000 kVA", "Nos", "BHEL", "BHEL"),
            ("BHEL", "BHEL-TR-1150", "1000 KVA Distribution Transformer", "IS:2026 11KV/433V 1000KVA", "Numbers", "Crompton", "Crompton"),
        ],
    },
    {
        "category": "Fasteners", "material_type": "Stainless Steel", "attrs": {"Size": "M16x50"},
        "variants": [
            ("SAIL", "SAIL-FAS-201", "SS Hex Bolt M16x50", "ASTM A193 B8, M16x50mm", "Nos", "Unbrako", "Unbrako"),
            ("HAL", "HAL-FT-5541", "Hexagonal Bolt Stainless Steel M16x50", "A193 GR B8 M16X50", "Numbers", "Unbrako", "Unbrako"),
        ],
    },
    {
        "category": "Gaskets", "material_type": "Spiral Wound", "attrs": {"Size": "4 inch, 150#"},
        "variants": [
            ("IOCL", "IOCL-GSK-3101", "Spiral Wound Gasket CS/Graphite", "ASME B16.20, 4 inch, 150#", "Nos", "Lamons", "Lamons"),
            ("BPCL", "BPCL-GK-6690", "Gasket Spiral Wound CS + Graphite", "ASME B16.20 4IN CLASS150", "Numbers", "Lamons", "Lamons"),
        ],
    },
    {
        "category": "Industrial Chemicals", "material_type": "Corrosion Inhibitor", "attrs": {"Concentration": "40%"},
        "variants": [
            ("ONGC", "ONGC-CHM-701", "Corrosion Inhibitor, Oilfield Grade 40%", "API RP 14E, 40% active", "Liter", "Baker Hughes", "Bakercor"),
            ("GAIL", "GAIL-CH-330", "Oilfield Corrosion Inhibitor 40 Pct", "API-RP14E 40 PERCENT ACTIVE", "Litre", "Baker Hughes", "Bakercor"),
        ],
    },
]

# Standalone, non-duplicated materials to reach a realistic total catalogue size.
STANDALONE_TEMPLATES = [
    ("Pipes", "Carbon Steel", "Welded Pipe {n}mm OD", "ASTM A53 Grade B, {n}mm OD", "Meter"),
    ("Valves", "Ball", "Ball Valve {n}mm Full Bore", "API 6D, {n}mm, Class 150", "Nos"),
    ("Bearings", "Roller", "Cylindrical Roller Bearing NU-{n}", "NU2{n} ISO 15", "Nos"),
    ("Lubricants", "Industrial", "Hydraulic Oil ISO VG {n}", "IS 3098, ISO VG {n}", "Liter"),
    ("Flanges", "Carbon Steel", "Slip-On Flange {n} inch", "ASTM A105, {n} inch, 300#", "Nos"),
    ("Motors", "Induction", "Single Phase Motor {n} HP", "IE2, 230V, {n} HP", "Nos"),
    ("Pumps", "Reciprocating", "Dosing Pump {n} LPH", "API 675, {n} LPH capacity", "Nos"),
    ("Cables", "Aluminium", "AL Armoured Cable {n} sqmm", "IS 7098, {n} sq.mm, 1.1kV", "Meter"),
    ("Transformers", "Power", "Power Transformer {n} MVA", "IS 2026, {n} MVA, 33/11kV", "Nos"),
    ("Fasteners", "Carbon Steel", "Hex Nut M{n}", "IS 1364, M{n}", "Nos"),
    ("Gaskets", "Rubber", "Rubber Gasket {n} inch", "IS 638, {n} inch, EPDM", "Nos"),
    ("Industrial Chemicals", "Scale Inhibitor", "Scale Inhibitor Grade {n}", "NACE TM0374, Grade {n}", "Liter"),
]


def get_or_create_roles(db) -> dict[str, Role]:
    roles = {}
    for name, description in ROLES:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()
        roles[name] = role
    db.commit()
    return roles


def get_or_create_cpses(db) -> dict[str, CPSEOrganization]:
    cpses = {}
    for code, name, sector in CPSES:
        cpse = db.query(CPSEOrganization).filter(CPSEOrganization.code == code).first()
        if not cpse:
            cpse = CPSEOrganization(code=code, name=name, sector=sector)
            db.add(cpse)
            db.flush()
        cpses[code] = cpse
    db.commit()
    return cpses


def get_or_create_users(db, roles: dict[str, Role], cpses: dict[str, CPSEOrganization]) -> dict[str, User]:
    users = {}
    for username, email, full_name, password, role_name, cpse_code in USERS:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role_id=roles[role_name].id,
                cpse_id=cpses[cpse_code].id if cpse_code else None,
            )
            db.add(user)
            db.flush()
        users[username] = user
    db.commit()
    return users


def _create_material(db, cpses, uploader, code, description, specification, category, uom, cpse_code, manufacturer, brand, material_type, attrs) -> Material:
    existing = db.query(Material).filter(Material.material_code == code).first()
    if existing:
        return existing
    material = Material(
        material_code=code,
        description=description,
        normalized_description=normalization.normalize_description(description),
        specification=specification,
        normalized_specification=normalization.normalize_specification(specification),
        category=category,
        normalized_category=normalization.normalize_category(category),
        uom=uom,
        normalized_uom=normalization.normalize_uom(uom),
        cpse_id=cpses[cpse_code].id,
        manufacturer=manufacturer,
        brand=brand,
        material_type=material_type,
        status="PENDING",
        created_by=uploader.id if uploader else None,
    )
    db.add(material)
    db.flush()
    for key, value in (attrs or {}).items():
        db.add(MaterialAttribute(material_id=material.id, attr_key=key, attr_value=value))
    db.commit()
    db.refresh(material)
    return material


def seed_materials(db, cpses, users) -> list[Material]:
    uploader_by_cpse = {
        "IOCL": users["iocl.user"], "ONGC": users["ongc.user"], "BPCL": users["bpcl.user"],
        "HPCL": users["hpcl.user"], "SAIL": users["sail.user"],
    }
    created: list[Material] = []

    for group in DUPLICATE_GROUPS:
        for cpse_code, code, description, specification, uom, manufacturer, brand in group["variants"]:
            uploader = uploader_by_cpse.get(cpse_code, users["admin"])
            material = _create_material(
                db, cpses, uploader, code, description, specification, group["category"], uom,
                cpse_code, manufacturer, brand, group["material_type"], group["attrs"],
            )
            created.append(material)

    cpse_cycle = list(cpses.keys())
    counter = 0
    for category, material_type, desc_tpl, spec_tpl, uom in STANDALONE_TEMPLATES:
        for n in (15, 20, 25, 32, 40, 50, 65, 80):
            counter += 1
            cpse_code = cpse_cycle[counter % len(cpse_cycle)]
            uploader = uploader_by_cpse.get(cpse_code, users["admin"])
            code = f"{cpse_code}-GEN-{1000 + counter}"
            description = desc_tpl.format(n=n)
            specification = spec_tpl.format(n=n)
            material = _create_material(
                db, cpses, uploader, code, description, specification, category, uom,
                cpse_code, "Various", "Generic", material_type, {},
            )
            created.append(material)

    # --- Demo 2: engineered ~90% match (spec section 39) --------------------------------
    demo2_a = _create_material(
        db, cpses, users["iocl.user"], "IOCL-VLV-9090", "Gate Valve Cast Steel Body",
        "ASTM A216 WCB, 6 inch, Class 300", "Valves", "Nos", "IOCL", "L&T Valves", "Leader", "Cast Steel",
        {"End Connection": "Flanged"},
    )
    demo2_b = _create_material(
        db, cpses, users["ongc.user"], "ONGC-VLV-9091", "Cast Steel Gate Valve, Flanged Ends",
        "A216 Gr WCB, 6 inch, Class 150", "Valves", "Numbers", "ONGC", "Audco", "Audco", "Cast Steel",
        {"End Connection": "Flanged"},
    )
    created += [demo2_a, demo2_b]

    # --- Demo 3: engineered low-confidence / no-match case (spec section 40) ------------
    demo3_a = _create_material(
        db, cpses, users["iocl.user"], "IOCL-PIP-5501", "Stainless Steel Welded Pipe",
        "ASTM A312 TP304, 6 inch, Schedule 10", "Pipes", "Meter", "IOCL", "Ratnamani", "Ratnamani",
        "Stainless Steel", {"Schedule": "SCH 10"},
    )
    demo3_b = _create_material(
        db, cpses, users["hpcl.user"], "HPCL-CBL-5502", "PVC Insulated Electrical Cable",
        "IS 694, 3 Core x 2.5 sq.mm, 1100V", "Cables", "Meter", "HPCL", "Finolex", "Finolex",
        "PVC", {"Cores": "3"},
    )
    created += [demo3_a, demo3_b]

    return created


def run_ai_pipeline(db, materials: list[Material]) -> None:
    # Pass 1: generate every material's embedding first. Without this, whichever
    # material in a duplicate group happens to be processed first would see an
    # empty candidate pool (nothing else has an embedding yet) and be scored
    # NO_COMMON_CODE, even though its sibling materials exist a few rows later.
    logger.info("Generating embeddings for %s materials...", len(materials))
    for material in materials:
        ensure_embeddings(db, material)

    logger.info("Running AI analysis pipeline for %s materials...", len(materials))
    for i, material in enumerate(materials, start=1):
        analyze_material(db, material.id)
        if i % 20 == 0:
            logger.info("  ... %s/%s analyzed", i, len(materials))
    logger.info("AI analysis complete.")


def main() -> None:
    Base.metadata.create_all(bind=engine)  # safety net if migrations haven't run yet
    db = SessionLocal()
    try:
        ensure_sequence(db)
        roles = get_or_create_roles(db)
        cpses = get_or_create_cpses(db)
        users = get_or_create_users(db, roles, cpses)
        materials = seed_materials(db, cpses, users)
        logger.info("Seeded %s CPSEs, %s users, %s materials", len(cpses), len(users), len(materials))
        run_ai_pipeline(db, materials)

        logger.info("=" * 70)
        logger.info("DEMO LOGIN CREDENTIALS")
        for username, _, full_name, password, role_name, _ in USERS:
            logger.info("  %-14s / %-12s  (%s - %s)", username, password, full_name, role_name)
        logger.info("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
