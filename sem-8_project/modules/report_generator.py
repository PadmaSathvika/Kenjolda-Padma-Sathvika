import os
from datetime import datetime



# ============================
# Generate full report
# ============================


def generate_report(question, topic, answer, compound_data, gene_id,
                    pdb_ids, pubmed_ids, downloaded_files,
                    cleaned_files, pdb_info, rag_results, docking_results=None):


    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_filename = f"report_{topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"


    report = ""
    report += "=" * 70 + "\n"
    report += "       AgentDKI DRUG DISCOVERY RESEARCH REPORT\n"
    report += "=" * 70 + "\n"
    report += f"Generated On  : {timestamp}\n"
    report += f"Query         : {question}\n"
    report += f"Topic         : {topic}\n"
    report += "=" * 70 + "\n\n"


    # ============================
    # Scientific Answer
    # ============================
    report += "SCIENTIFIC ANSWER\n"
    report += "-" * 70 + "\n"
    report += f"{answer}\n\n"


    # ============================
    # Compound Data
    # ============================
    report += "COMPOUND DATA (PubChem)\n"
    report += "-" * 70 + "\n"
    if compound_data:
        report += f"Name            : {compound_data['compound']}\n"
        report += f"Molecular Formula: {compound_data['formula']}\n"
        report += f"Molecular Weight : {compound_data['weight']} g/mol\n"
        report += f"PubChem Link     : https://pubchem.ncbi.nlm.nih.gov/compound/{compound_data['compound']}\n"
    else:
        report += "No compound data found.\n"
    report += "\n"


    # ============================
    # Gene Data
    # ============================
    report += "GENE DATA (NCBI)\n"
    report += "-" * 70 + "\n"
    if gene_id:
        report += f"NCBI Gene ID : {gene_id}\n"
        report += f"NCBI Link    : https://www.ncbi.nlm.nih.gov/gene/{gene_id}\n"
    else:
        report += "No gene data found.\n"
    report += "\n"


    # ============================
    # Protein Structures
    # ============================
    report += "PROTEIN STRUCTURES (PDB)\n"
    report += "-" * 70 + "\n"
    if pdb_ids:
        for i, pdb in enumerate(pdb_ids):
            report += f"Structure {i+1}  : {pdb}\n"
            report += f"PDB Link     : https://www.rcsb.org/structure/{pdb}\n"
            if pdb_info and i < len(pdb_info) and pdb_info[i]:
                info = pdb_info[i]
                report += f"Protein Name : {info['protein_name']}\n"
                report += f"Chains       : {info['num_chains']}\n"
                report += f"Residues     : {info['num_residues']}\n"
                report += f"Atoms        : {info['num_atoms']}\n"
            report += "\n"
    else:
        report += "No protein structures found.\n\n"


    # ============================
    # Downloaded & Cleaned Files
    # ============================
    report += "DOWNLOADED PDB FILES\n"
    report += "-" * 70 + "\n"
    if downloaded_files:
        for f in downloaded_files:
            report += f"  - {f}\n"
    else:
        report += "No files downloaded.\n"
    report += "\n"


    report += "CLEANED PDB FILES\n"
    report += "-" * 70 + "\n"
    if cleaned_files:
        for f in cleaned_files:
            report += f"  - {f}\n"
    else:
        report += "No cleaned files.\n"
    report += "\n"


    # ============================
    # Docking Results
    # ============================
    report += "MOLECULAR DOCKING RESULTS\n"
    report += "-" * 70 + "\n"
    if docking_results:
        for dr in docking_results:
            report += f"  {dr}\n"
    else:
        report += "No docking results available.\n"
    report += "\n"


    # ============================
    # PubMed Papers
    # ============================
    report += "PUBMED PAPERS\n"
    report += "-" * 70 + "\n"
    if pubmed_ids:
        for pid in pubmed_ids[:10]:
            report += f"  - https://pubmed.ncbi.nlm.nih.gov/{pid}/\n"
    else:
        report += "No papers found.\n"
    report += "\n"


    # ============================
    # RAG Results with Metadata
    # ============================
    report += "TOP RELEVANT RESEARCH ABSTRACTS (RAG)\n"
    report += "-" * 70 + "\n"
    if rag_results:
        for i, r in enumerate(rag_results, 1):
            meta = r.get("metadata", {})
            report += f"\nResult {i}:\n"
            report += f"  Title   : {meta.get('title', 'N/A')}\n"
            report += f"  Authors : {meta.get('authors', 'N/A')}\n"
            report += f"  Journal : {meta.get('journal', 'N/A')}\n"
            report += f"  Year    : {meta.get('year', 'N/A')}\n"
            report += f"  PubMed  : https://pubmed.ncbi.nlm.nih.gov/{meta.get('id', '')}/\n"
            report += f"  Abstract: {r['text'][:400]}...\n"
    else:
        report += "No RAG results available.\n"
    report += "\n"


    report += "=" * 70 + "\n"
    report += "END OF REPORT\n"
    report += "=" * 70 + "\n"


    # Save report
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)


    print(f"\n[Report] Saved to: {report_filename}")


    return report_filename