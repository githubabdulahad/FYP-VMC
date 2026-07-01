import jsPDF from "jspdf";

export const generatePDF = (reportData: any, filename: string) => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - 2 * margin;
  let yPos = margin;

  const addText = (
    text: string,
    fontSize: number,
    isBold: boolean = false,
    isHeading: boolean = false
  ) => {
    doc.setFontSize(fontSize);
    doc.setFont(undefined, isBold ? "bold" : "normal");
    const lines = doc.splitTextToSize(text, contentWidth);

    if (yPos + lines.length * 5 > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
    }

    doc.text(lines, margin, yPos);
    yPos += lines.length * 5 + (isHeading ? 3 : 2);
  };

  addText(`Medical Coding Report`, 16, true, true);
  addText(`Document: ${reportData.file_name}`, 11, true);
  addText(
    `Date: ${new Date(reportData.created_at).toLocaleDateString()}`,
    10
  );
  yPos += 3;

  if (reportData.soap_note) {
    addText("SOAP NOTE", 12, true, true);
    const soap = reportData.soap_note;

    if (soap.subjective) {
      addText("Subjective:", 10, true);
      addText(soap.subjective, 9);
    }
    if (soap.objective) {
      addText("Objective:", 10, true);
      addText(soap.objective, 9);
    }
    if (soap.assessment) {
      addText("Assessment:", 10, true);
      addText(soap.assessment, 9);
    }
    if (soap.plan) {
      addText("Plan:", 10, true);
      addText(soap.plan, 9);
    }

    yPos += 3;
  }

  if (reportData.icd_codes && reportData.icd_codes.length > 0) {
    addText("ICD-10 DIAGNOSIS CODES", 12, true, true);
    reportData.icd_codes.forEach(
      (code: { code: string; description: string; confidence: number }) => {
        addText(
          `${code.code} - ${code.description} (${Math.round(
            code.confidence * 100
          )}%)`,
          9
        );
      }
    );
    yPos += 3;
  }

  if (reportData.cpt_codes && reportData.cpt_codes.length > 0) {
    addText("CPT PROCEDURE CODES", 12, true, true);
    reportData.cpt_codes.forEach(
      (code: { code: string; description: string; confidence: number }) => {
        addText(
          `${code.code} - ${code.description} (${Math.round(
            code.confidence * 100
          )}%)`,
          9
        );
      }
    );
  }

  doc.save(filename);
};      