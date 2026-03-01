import requests
import os


def download_structures(pdb_ids):

    folder = "pdb_files"

    if not os.path.exists(folder):
        os.makedirs(folder)

    downloaded_files = []

    for pdb_id in pdb_ids:

        pdb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
        cif_url = f"https://files.rcsb.org/download/{pdb_id}.cif"

        pdb_response = requests.get(pdb_url)

        if pdb_response.status_code == 200:

            filepath = os.path.join(folder, pdb_id + ".pdb")

            with open(filepath, "w") as f:
                f.write(pdb_response.text)

            downloaded_files.append(filepath)

        else:

            cif_response = requests.get(cif_url)

            if cif_response.status_code == 200:

                filepath = os.path.join(folder, pdb_id + ".cif")

                with open(filepath, "w") as f:
                    f.write(cif_response.text)

                downloaded_files.append(filepath)

    return downloaded_files