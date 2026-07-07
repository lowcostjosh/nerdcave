import { FacultyDashboard } from "@/components/faculty/FacultyDashboard";

export default async function FacultyPage({
  searchParams,
}: {
  searchParams: Promise<{ courseId?: string }>;
}) {
  const { courseId } = await searchParams;
  return <FacultyDashboard initialCourseId={courseId} />;
}
