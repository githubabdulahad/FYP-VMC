import type { ReviewStatus } from "../../../types/document";

export const statusConfig: Record <
  ReviewStatus,
  { label: string; dot: string; bg: string; text: string }
> = {
  pending: {
    label: "Ready for Review",
    dot: "bg-blue-500",
    bg: "bg-blue-50",
    text: "text-blue-800",
  },
  approved: {
    label: "Approved",
    dot: "bg-teal-500",
    bg: "bg-teal-50",
    text: "text-teal-800",
  },
  rejected: {
    label: "Rejected",
    dot: "bg-red-400",
    bg: "bg-red-50",
    text: "text-red-800",
  },
  revised: {
    label: "Revised",
    dot: "bg-purple-400",
    bg: "bg-purple-50",
    text: "text-purple-800",
  },
};