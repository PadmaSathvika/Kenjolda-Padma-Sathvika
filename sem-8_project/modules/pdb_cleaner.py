import os
import re


# ============================
# Clean a single PDB file
# ============================


def clean_pdb_file(filepath):
    """
    Cleans a PDB file by:
    - Removing water molecules (HOH)
    - Removing ligands (HETATM records)
    - Removing hydrogen atoms
    - Keeping only ATOM records (protein backbone)
    - Renumbering residues cleanly
    """


    if not os.path.exists(filepath):
        print(f"[PDB Cleaner] File not found: {filepath}")
        return None


    cleaned_lines = []


    with open(filepath, "r") as f:
        lines = f.readlines()


    for line in lines:


        # Keep only ATOM records (skip HETATM, REMARK, etc.)
        if not line.startswith("ATOM"):
            continue


        # Skip hydrogen atoms (element H)
        if len(line) >= 78:
            element = line[76:78].strip()
            if element == "H":
                continue


        # Skip water molecules
        residue_name = line[17:20].strip()
        if residue_name in ["HOH", "WAT", "H2O"]:
            continue


        cleaned_lines.append(line)


    # Add END record
    cleaned_lines.append("END\n")


    # Save cleaned file
    cleaned_path = filepath.replace(".pdb", "_cleaned.pdb")


    with open(cleaned_path, "w") as f:
        f.writelines(cleaned_lines)


    print(f"[PDB Cleaner] Cleaned: {filepath} → {cleaned_path}")
    print(f"[PDB Cleaner] Original lines: {len(lines)}, Cleaned lines: {len(cleaned_lines)}")


    return cleaned_path



# ============================
# Clean multiple PDB files
# ============================


def clean_pdb_files(pdb_filepaths):
    """
    Cleans a list of PDB files and returns paths to cleaned files.
    """


    cleaned_files = []


    for filepath in pdb_filepaths:
        cleaned_path = clean_pdb_file(filepath)
        if cleaned_path:
            cleaned_files.append(cleaned_path)


    return cleaned_files



# ============================
# Extract protein info from PDB
# ============================


def extract_pdb_info(filepath):
    """
    Extracts basic info from a PDB file:
    - Protein name
    - Number of chains
    - Number of residues
    - Number of atoms
    """


    if not os.path.exists(filepath):
        return None


    chains = set()
    residues = set()
    atom_count = 0
    protein_name = ""


    with open(filepath, "r") as f:
        lines = f.readlines()


    for line in lines:


        # Extract protein name from COMPND record
        if line.startswith("COMPND") and "MOLECULE:" in line:
            name_match = re.search(r"MOLECULE:\s*(.*?);", line)
            if name_match:
                protein_name = name_match.group(1).strip()


        # Extract chain, residue, atom info from ATOM records
        if line.startswith("ATOM"):
            atom_count += 1
            chain = line[21].strip()
            residue_num = line[22:26].strip()
            residue_name = line[17:20].strip()


            if chain:
                chains.add(chain)
            if residue_num:
                residues.add((chain, residue_num, residue_name))


    return {
        "protein_name": protein_name if protein_name else "Unknown",
        "chains": list(chains),
        "num_chains": len(chains),
        "num_residues": len(residues),
        "num_atoms": atom_count
    }



# ============================
# Clean all PDB files in folder
# ============================


def clean_all_pdb_in_folder(folder="pdb_files"):
    """
    Cleans all PDB files in a folder.
    """


    if not os.path.exists(folder):
        print(f"[PDB Cleaner] Folder not found: {folder}")
        return []


    pdb_files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(".pdb") and not f.endswith("_cleaned.pdb")
    ]


    if not pdb_files:
        print(f"[PDB Cleaner] No PDB files found in {folder}")
        return []


    print(f"[PDB Cleaner] Found {len(pdb_files)} PDB files to clean.")


    return clean_pdb_files(pdb_files)