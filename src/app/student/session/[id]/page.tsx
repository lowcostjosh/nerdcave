import { SessionWorkspace } from "@/components/student/SessionWorkspace";

export default async function StudentSessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <SessionWorkspace sessionId={id} />;
}
