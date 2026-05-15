import os
import shutil
import subprocess
import requests


# ============================
# Ligand download & conversion
# ============================

def download_ligand(compound_name, folder="pdb_files"):

    if not os.path.exists(folder):
        os.makedirs(folder)

    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound_name}/SDF"

    try:

        response = requests.get(url, timeout=10)

        if response.status_code == 200:

            filepath = os.path.abspath(
                os.path.join(folder, f"{compound_name}_ligand.sdf")
            )

            with open(filepath, "w") as f:
                f.write(response.text)

            print(f"[Docking] Ligand downloaded: {filepath}")

            return filepath

        return None

    except Exception as e:

        print(f"[Docking] Ligand download error: {e}")

        return None


# ============================
# Ligand Preparation
# ============================

def convert_ligand_to_pdbqt(sdf_path):

    if not sdf_path or not os.path.exists(sdf_path):
        return None

    pdb_path = sdf_path.replace(".sdf", ".pdb")

    pdbqt_path = sdf_path.replace(".sdf", ".pdbqt")

    try:

        subprocess.run(
            f'obabel "{sdf_path}" -O "{pdb_path}" --gen3d -h',
            shell=True,
            check=True
        )

        subprocess.run(
            f'obabel "{pdb_path}" -O "{pdbqt_path}"',
            shell=True,
            check=True
        )

        print(f"[Docking] Ligand prepared: {pdbqt_path}")

        return pdbqt_path

    except Exception as e:

        print(f"[Docking] Ligand conversion error: {e}")

        return None


# ============================
# Stable Receptor Preparation
# ============================

def convert_receptor_to_pdbqt(pdb_path):

    """
    Stable receptor preparation for AutoDock Vina.
    Simpler conversion gives more reliable docking.
    """

    if not pdb_path or not os.path.exists(pdb_path):
        return None

    pdbqt_path = pdb_path.replace(".pdb", ".pdbqt")

    try:

        subprocess.run(
            f'obabel "{pdb_path}" -O "{pdbqt_path}" -xr',
            shell=True,
            check=True
        )

        print(f"[Docking] Receptor prepared: {pdbqt_path}")

        return pdbqt_path

    except Exception as e:

        print(f"[Docking] Receptor conversion error: {e}")

        return None


# ============================
# Protein Center + Box Size
# ============================

def get_protein_center_and_size(pdbqt_path):

    x_list, y_list, z_list = [], [], []

    try:

        with open(pdbqt_path, 'r') as f:

            for line in f:

                if line.startswith("ATOM") or line.startswith("HETATM"):

                    try:

                        x_list.append(float(line[30:38]))
                        y_list.append(float(line[38:46]))
                        z_list.append(float(line[46:54]))

                    except ValueError:
                        continue

        if not x_list:
            return 0.0, 0.0, 0.0, 30.0

        cx = sum(x_list) / len(x_list)
        cy = sum(y_list) / len(y_list)
        cz = sum(z_list) / len(z_list)

        span = max(
            max(x_list) - min(x_list),
            max(y_list) - min(y_list),
            max(z_list) - min(z_list)
        )

        size = min(max(span * 0.6, 24.0), 40.0)

        print(f"[Docking] Protein center: ({cx:.2f}, {cy:.2f}, {cz:.2f})")

        return cx, cy, cz, size

    except Exception as e:

        print(f"[Docking] Center calc error: {e}")

        return 0.0, 0.0, 0.0, 30.0


# ============================
# AutoDock Vina Runner
# ============================

def run_vina(
    receptor_pdbqt,
    ligand_pdbqt,
    cx,
    cy,
    cz,
    box_size=30,
    output_folder="docking_results"
):

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_path = os.path.abspath(
        os.path.join(
            output_folder,
            os.path.basename(receptor_pdbqt).replace(".pdbqt", "_docked.pdbqt")
        )
    )

    log_path = output_path.replace(".pdbqt", "_log.txt")

    try:

        cmd = (
            f'vina '
            f'--receptor "{receptor_pdbqt}" '
            f'--ligand "{ligand_pdbqt}" '
            f'--out "{output_path}" '
            f'--log "{log_path}" '
            f'--center_x {cx:.3f} '
            f'--center_y {cy:.3f} '
            f'--center_z {cz:.3f} '
            f'--size_x {box_size} '
            f'--size_y {box_size} '
            f'--size_z {box_size} '
            f'--exhaustiveness 16 '
            f'--num_modes 9'
        )

        print("[Docking] Running AutoDock Vina...")

        subprocess.run(
            cmd,
            shell=True,
            check=True,
            timeout=600
        )

        print(f"[Docking] Vina docking complete: {output_path}")

        return output_path, log_path

    except Exception as e:

        print(f"[Docking] Vina error: {e}")

        return None


# ============================
# Better Docking Parsing
# ============================

def parse_docking_results(log_path):

    if not log_path or not os.path.exists(log_path):
        return []

    results = []

    try:

        with open(log_path, "r") as f:
            lines = f.readlines()

        capture = False

        for line in lines:

            if "mode |   affinity" in line.lower():
                capture = True
                continue

            if capture:

                parts = line.strip().split()

                if len(parts) < 4:
                    continue

                try:

                    mode = int(parts[0])

                    affinity = float(parts[1])

                    results.append(
                        f"Mode {mode}: Binding Affinity = {affinity:.2f} kcal/mol"
                    )

                except:
                    continue

        return results

    except Exception as e:

        print(f"[Docking] Parsing error: {e}")

        return []


# ============================
# Pose Extraction
# ============================

def extract_top_pose_to_pdb(docked_pdbqt, output_pdb=None):

    if not docked_pdbqt or not os.path.exists(docked_pdbqt):
        return None

    if output_pdb is None:
        output_pdb = docked_pdbqt.replace(".pdbqt", "_pose1.pdb")

    try:

        tmp = output_pdb + ".tmp.pdb"

        subprocess.run(
            f'obabel "{docked_pdbqt}" -O "{tmp}" -f 1 -l 1',
            shell=True,
            check=True,
            timeout=60
        )

        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:

            shutil.move(tmp, output_pdb)

            return output_pdb

    except Exception as e:

        print(f"[Docking] Pose extraction error: {e}")

    return None


# ============================
# Ligand fallback placement
# ============================

def translate_ligand_to_center(
    ligand_pdbqt,
    cx,
    cy,
    cz,
    output_pdb=None
):

    if not ligand_pdbqt or not os.path.exists(ligand_pdbqt):
        return None

    if output_pdb is None:
        output_pdb = ligand_pdbqt.replace(".pdbqt", "_placed.pdb")

    try:

        atom_lines = []

        xs, ys, zs = [], [], []

        with open(ligand_pdbqt, 'r') as f:

            for line in f:

                if line.startswith("ATOM") or line.startswith("HETATM"):

                    try:

                        xs.append(float(line[30:38]))
                        ys.append(float(line[38:46]))
                        zs.append(float(line[46:54]))

                        atom_lines.append(line)

                    except ValueError:
                        continue

        if not atom_lines:
            return None

        lx = sum(xs) / len(xs)
        ly = sum(ys) / len(ys)
        lz = sum(zs) / len(zs)

        dx, dy, dz = cx - lx, cy - ly, cz - lz

        shifted = []

        for line in atom_lines:

            try:

                x = float(line[30:38]) + dx
                y = float(line[38:46]) + dy
                z = float(line[46:54]) + dz

                new_line = (
                    line[:30]
                    + f"{x:8.3f}{y:8.3f}{z:8.3f}"
                    + line[54:66].rstrip()
                    + "\n"
                )

                if new_line.startswith("ATOM"):
                    new_line = "HETATM" + new_line[6:]

                shifted.append(new_line)

            except ValueError:
                continue

        with open(output_pdb, "w") as f:
            f.writelines(shifted)
            f.write("END\n")

        print(f"[Docking] Ligand translated into pocket: {output_pdb}")

        return output_pdb

    except Exception as e:

        print(f"[Docking] Translation error: {e}")

        return None


# ============================
# Main Docking Pipeline
# ============================

def run_docking_pipeline(compound_name, cleaned_pdb_files):

    print("\n[Docking Pipeline] Starting...")

    results = []

    last_output = None

    last_receptor = None

    sdf = download_ligand(compound_name)

    if not sdf:
        return ["Ligand download failed"], None, None

    ligand = convert_ligand_to_pdbqt(sdf)

    if not ligand:

        if cleaned_pdb_files:
            return ["Ligand conversion failed"], None, cleaned_pdb_files[0]

        return ["Ligand conversion failed"], None, None

    for pdb in cleaned_pdb_files[:1]:

        receptor = convert_receptor_to_pdbqt(pdb)

        if not receptor:
            continue

        cx, cy, cz, size = get_protein_center_and_size(receptor)

        box_size = int(max(24, min(size, 40)))

        vina_result = run_vina(
            receptor,
            ligand,
            cx,
            cy,
            cz,
            box_size=box_size
        )

        if vina_result:

            output_pdbqt, log = vina_result

            scores = parse_docking_results(log)

            pose_pdb = extract_top_pose_to_pdb(output_pdbqt)

            last_output = pose_pdb if pose_pdb else output_pdbqt

            last_receptor = receptor

            if scores:
                results.extend(scores)
            else:
                results.append("Docking completed")

        else:

            print("[Docking] Using fallback ligand placement.")

            placed = translate_ligand_to_center(
                ligand,
                cx,
                cy,
                cz
            )

            last_output = placed if placed else ligand

            last_receptor = receptor

            results.append(
                "Binding affinity simulated (fallback visualization)."
            )

    return results, last_output, last_receptor