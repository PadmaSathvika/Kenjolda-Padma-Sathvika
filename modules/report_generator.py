def generate_report(compound_data, gene_id, pubmed_ids, pdb_ids, files):

    report = "Drug Discovery Agent Report\n"
    report += "===========================\n\n"

    report += "Compound Info:\n"

    if compound_data:
        report += f"Name: {compound_data['compound']}\n"
        report += f"Formula: {compound_data['formula']}\n"
        report += f"Weight: {compound_data['weight']}\n"

    report += "\nGene Info:\n"
    report += f"Gene ID: {gene_id}\n\n"

    report += "PubMed Papers:\n"
    for pid in pubmed_ids:
        report += pid + "\n"

    report += "\nPDB Structures:\n"
    for pdb in pdb_ids:
        report += pdb + "\n"

    report += "\nDownloaded Files:\n"
    for file in files:
        report += file + "\n"

    with open("report.txt", "w") as f:
        f.write(report)