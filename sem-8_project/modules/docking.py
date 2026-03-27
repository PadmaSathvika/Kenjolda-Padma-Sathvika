import os
import subprocess
import requests


# ============================
# Download ligand from PubChem
# ============================

def download_ligand(compound_name, folder="pdb_files"):
    """
    Downloads ligand SDF file from PubChem for docking.
    """

    if not os.path.exists(folder):
        os.makedirs(folder)

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound_name}/SDF"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            filepath = os.path.join(folder, f"{compound_name}_ligand.sdf")

            with open(filepath, "w") as f:
                f.write(response.text)

            print(f"[Docking] Ligand downloaded: {filepath}")
            return filepath

        else:
            print(f"[Docking] Could not download ligand for: {compound_name}")
            return None

    except Exception as e:
        print(f"[Docking] Ligand download error: {str(e)}")
        return None


# ============================
# Convert SDF to PDBQT using Open Babel
# ============================

def convert_ligand_to_pdbqt(sdf_path):
    """
    Converts SDF ligand file to PDBQT format for AutoDock Vina.
    Requires Open Babel to be installed.
    """

    if not sdf_path or not os.path.exists(sdf_path):
        print("[Docking] SDF file not found.")
        return None

    pdbqt_path = sdf_path.replace(".sdf", ".pdbqt")

    try:
        subprocess.run([
            "obabel",
            sdf_path,
            "-O", pdbqt_path,
            "--gen3d",
            "-h"
        ], check=True, capture_output=True)

        print(f"[Docking] Ligand converted to PDBQT: {pdbqt_path}")
        return pdbqt_path

    except FileNotFoundError:
        print("[Docking] Open Babel not found. Please install it.")
        print("[Docking] Download from: https://openbabel.org/")
        return None

    except subprocess.CalledProcessError as e:
        print(f"[Docking] Conversion error: {e}")
        return None


# ============================
# Convert cleaned PDB to PDBQT
# ============================

def convert_receptor_to_pdbqt(pdb_path):
    """
    Converts cleaned PDB receptor file to PDBQT format for AutoDock Vina.
    Requires Open Babel to be installed.
    """

    if not pdb_path or not os.path.exists(pdb_path):
        print("[Docking] PDB file not found.")
        return None

    pdbqt_path = pdb_path.replace(".pdb", ".pdbqt")

    try:
        subprocess.run([
            "obabel",
            pdb_path,
            "-O", pdbqt_path,
            "-xr"
        ], check=True, capture_output=True)

        print(f"[Docking] Receptor converted to PDBQT: {pdbqt_path}")
        return pdbqt_path

    except FileNotFoundError:
        print("[Docking] Open Babel not found. Please install it.")
        return None

    except subprocess.CalledProcessError as e:
        print(f"[Docking] Conversion error: {e}")
        return None


# ============================
# Run AutoDock Vina
# ============================

def run_vina(receptor_pdbqt, ligand_pdbqt, output_folder="docking_results"):
    """
    Runs AutoDock Vina for molecular docking.
    Requires AutoDock Vina to be installed.
    """

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if not receptor_pdbqt or not os.path.exists(receptor_pdbqt):
        print("[Docking] Receptor PDBQT not found.")
        return None

    if not ligand_pdbqt or not os.path.exists(ligand_pdbqt):
        print("[Docking] Ligand PDBQT not found.")
        return None

    output_path = os.path.join(
        output_folder,
        os.path.basename(receptor_pdbqt).replace(".pdbqt", "_docked.pdbqt")
    )

    log_path = output_path.replace(".pdbqt", "_log.txt")

    try:
        result = subprocess.run([
            "vina",
            "--receptor", receptor_pdbqt,
            "--ligand", ligand_pdbqt,
            "--out", output_path,
            "--log", log_path,
            "--center_x", "0",
            "--center_y", "0",
            "--center_z", "0",
            "--size_x", "20",
            "--size_y", "20",
            "--size_z", "20",
            "--exhaustiveness", "8"
        ], check=True, capture_output=True, text=True)

        print(f"[Docking] Docking complete: {output_path}")
        return output_path, log_path

    except FileNotFoundError:
        print("[Docking] AutoDock Vina not found.")
        print("[Docking] Download from: https://vina.scripps.edu/")
        return None

    except subprocess.CalledProcessError as e:
        print(f"[Docking] Vina error: {e}")
        return None


# ============================
# Parse docking results
# ============================

def parse_docking_results(log_path):
    """
    Parses AutoDock Vina log file to extract binding affinities.
    """

    if not log_path or not os.path.exists(log_path):
        print("[Docking] Log file not found.")
        return []

    results = []

    with open(log_path, "r") as f:
        lines = f.readlines()

    parsing = False

    for line in lines:
        if "-----+------------+----------+----------" in line:
            parsing = True
            continue

        if parsing:
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    mode = parts[0]
                    affinity = parts[1]
                    results.append(
                        f"Mode {mode}: Binding Affinity = {affinity} kcal/mol"
                    )
                except:
                    continue

    return results


# ============================
# Full automated docking pipeline
# ============================

def run_docking_pipeline(compound_name, cleaned_pdb_files):
    """
    Runs the full automated docking pipeline:
    1. Download ligand from PubChem
    2. Convert ligand to PDBQT
    3. Convert receptor to PDBQT
    4. Run AutoDock Vina
    5. Parse and return results
    """

    print("\n[Docking Pipeline] Starting automated docking...")

    docking_results = []

    # Step 1: Download ligand
    sdf_path = download_ligand(compound_name)

    if not sdf_path:
        docking_results.append("Ligand download failed.")
        return docking_results

    # Step 2: Convert ligand to PDBQT
    ligand_pdbqt = convert_ligand_to_pdbqt(sdf_path)

    if not ligand_pdbqt:
        docking_results.append(
            "Ligand conversion failed. Open Babel may not be installed."
        )
        return docking_results

    # Step 3: Run docking for each cleaned PDB
    for pdb_path in cleaned_pdb_files[:2]:  # Limit to first 2 structures

        print(f"\n[Docking Pipeline] Docking with: {pdb_path}")

        # Convert receptor
        receptor_pdbqt = convert_receptor_to_pdbqt(pdb_path)

        if not receptor_pdbqt:
            docking_results.append(
                f"Receptor conversion failed for {pdb_path}."
            )
            continue

        # Run Vina
        result = run_vina(receptor_pdbqt, ligand_pdbqt)

        if result:
            output_path, log_path = result
            scores = parse_docking_results(log_path)

            if scores:
                for score in scores[:3]:  # Top 3 poses
                    docking_results.append(
                        f"{os.path.basename(pdb_path)}: {score}"
                    )
            else:
                docking_results.append(
                    f"{os.path.basename(pdb_path)}: Docking complete but no scores parsed."
                )
        else:
            docking_results.append(
                f"Docking failed for {os.path.basename(pdb_path)}. "
                f"AutoDock Vina may not be installed."
            )

    return docking_results