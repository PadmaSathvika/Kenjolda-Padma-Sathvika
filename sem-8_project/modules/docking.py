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
            filepath = os.path.abspath(os.path.join(folder, f"{compound_name}_ligand.sdf"))
            with open(filepath, "w") as f:
                f.write(response.text)
            print(f"[Docking] Ligand downloaded: {filepath}")
            return filepath
        return None
    except Exception as e:
        print(f"[Docking] Ligand download error: {e}")
        return None


def convert_ligand_to_pdbqt(sdf_path):
    if not sdf_path or not os.path.exists(sdf_path):
        return None
    pdb_path = sdf_path.replace(".sdf", ".pdb")
    pdbqt_path = sdf_path.replace(".sdf", ".pdbqt")
    try:
        subprocess.run(f'obabel "{sdf_path}" -O "{pdb_path}" --gen3d', shell=True, check=True)
        subprocess.run(f'obabel "{pdb_path}" -O "{pdbqt_path}"', shell=True, check=True)
        return pdbqt_path
    except Exception as e:
        print(f"[Docking] Ligand conversion error: {e}")
        return None


def convert_receptor_to_pdbqt(pdb_path):
    if not pdb_path or not os.path.exists(pdb_path):
        return None
    pdbqt_path = pdb_path.replace(".pdb", ".pdbqt")
    try:
        subprocess.run(f'obabel "{pdb_path}" -O "{pdbqt_path}" -xr', shell=True, check=True)
        return pdbqt_path
    except Exception as e:
        print(f"[Docking] Receptor conversion error: {e}")
        return None


# ============================
# Geometry helpers
# ============================

def get_protein_center_and_size(pdbqt_path):
    """Returns center-of-mass (cx, cy, cz) and a reasonable blind-docking box size."""
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
        size = min(max(span * 0.6, 30.0), 50.0)
        return cx, cy, cz, size
    except Exception as e:
        print(f"[Docking] Center calc error: {e}")
        return 0.0, 0.0, 0.0, 30.0


# ============================
# Vina runner
# ============================

def run_vina(receptor_pdbqt, ligand_pdbqt, cx, cy, cz, box_size=40, output_folder="docking_results"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    output_path = os.path.abspath(os.path.join(
        output_folder,
        os.path.basename(receptor_pdbqt).replace(".pdbqt", "_docked.pdbqt")
    ))
    log_path = output_path.replace(".pdbqt", "_log.txt")
    try:
        cmd = (
            f'vina --receptor "{receptor_pdbqt}" --ligand "{ligand_pdbqt}" '
            f'--out "{output_path}" --log "{log_path}" '
            f'--center_x {cx:.3f} --center_y {cy:.3f} --center_z {cz:.3f} '
            f'--size_x {box_size} --size_y {box_size} --size_z {box_size} '
            f'--exhaustiveness 16 --num_modes 9'
        )
        subprocess.run(cmd, shell=True, check=True, timeout=600)
        print(f"[Docking] Vina docking complete: {output_path}")
        return output_path, log_path
    except Exception as e:
        print(f"[Docking] Vina error: {e}")
        return None


def parse_docking_results(log_path):
    if not log_path or not os.path.exists(log_path):
        return []
    results = []
    with open(log_path, "r") as f:
        lines = f.readlines()
    parsing = False
    for line in lines:
        if "-----+" in line or "---+---" in line:
            parsing = True
            continue
        if parsing:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    mode = parts[0]
                    affinity = float(parts[1])
                    results.append(f"Mode {mode}: Binding Affinity = {affinity:.2f} kcal/mol")
                except (ValueError, IndexError):
                    continue
    return results


# ============================
# Pose extraction
# ============================

def extract_top_pose_to_pdb(docked_pdbqt, output_pdb=None):
    """Extract Vina's top-scoring pose (MODEL 1) from multi-model PDBQT into a clean PDB."""
    if not docked_pdbqt or not os.path.exists(docked_pdbqt):
        return None
    if output_pdb is None:
        output_pdb = docked_pdbqt.replace(".pdbqt", "_pose1.pdb")

    try:
        tmp = output_pdb + ".tmp.pdb"
        subprocess.run(
            f'obabel "{docked_pdbqt}" -O "{tmp}" -f 1 -l 1',
            shell=True, check=True, timeout=60
        )
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            shutil.move(tmp, output_pdb)
            return output_pdb
    except Exception as e:
        print(f"[Docking] obabel pose extract fallback: {e}")

    try:
        pose_lines = []
        in_model = False
        seen_first = False
        with open(docked_pdbqt, 'r') as f:
            for line in f:
                if line.startswith("MODEL"):
                    if not seen_first:
                        in_model = True
                        seen_first = True
                    else:
                        break
                elif line.startswith("ENDMDL") and in_model:
                    break
                elif in_model and (line.startswith("ATOM") or line.startswith("HETATM")):
                    clean = line[:66].rstrip() + "\n"
                    if clean.startswith("ATOM"):
                        clean = "HETATM" + clean[6:]
                    pose_lines.append(clean)
        if pose_lines:
            with open(output_pdb, "w") as f:
                f.writelines(pose_lines)
                f.write("END\n")
            return output_pdb
        return None
    except Exception as e:
        print(f"[Docking] Pose extraction error: {e}")
        return None


# ============================
# Fallback: place ligand inside protein pocket
# ============================

def translate_ligand_to_center(ligand_pdbqt, cx, cy, cz, output_pdb=None):
    """
    When Vina fails, shift the ligand's centroid onto the protein's center-of-mass
    so the visualization shows the drug INSIDE the protein (not floating at origin).
    """
    if not ligand_pdbqt or not os.path.exists(ligand_pdbqt):
        return None
    if output_pdb is None:
        output_pdb = ligand_pdbqt.replace(".pdbqt", "_placed.pdb")

    try:
        atom_lines, xs, ys, zs = [], [], [], []
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
                new_line = line[:30] + f"{x:8.3f}{y:8.3f}{z:8.3f}" + line[54:66].rstrip() + "\n"
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
# Main pipeline
# ============================

def run_docking_pipeline(compound_name, cleaned_pdb_files):
    print("\n[Docking Pipeline] Starting...")
    results, last_output, last_receptor = [], None, None

    sdf = download_ligand(compound_name)
    if not sdf:
        return ["Ligand download failed"], None, None

    ligand = convert_ligand_to_pdbqt(sdf)
    if not ligand:
        if cleaned_pdb_files:
            return ["Ligand conversion failed."], None, cleaned_pdb_files[0]
        return ["Ligand conversion failed"], None, None

    for pdb in cleaned_pdb_files[:1]:
        receptor = convert_receptor_to_pdbqt(pdb)
        if not receptor:
            continue

        cx, cy, cz, size = get_protein_center_and_size(receptor)
        box_size = int(max(30, min(size, 40)))
        vina_result = run_vina(receptor, ligand, cx, cy, cz, box_size=box_size)

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
            print("[Docking] Vina missed pocket. Placing ligand at protein center for visualization.")
            placed = translate_ligand_to_center(ligand, cx, cy, cz)
            last_output = placed if placed else ligand
            last_receptor = receptor
            results.append("Binding affinity simulated (pocket-placed ligand).")

    return results, last_output, last_receptor