import { StudentDrilldownView } from "@/components/faculty/StudentDrilldownView";

export default async function StudentDrilldownPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <StudentDrilldownView studentId={id} />;
}
