import { redirect } from "next/navigation";

// The home of the app is "Bugun" (today's routine); old links and bookmarks land there.
export default function Dashboard() {
  redirect("/routine");
}
