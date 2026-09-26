"use client";

import { useEffect } from "react";
import useSWR from "swr";

import { CoachAvatar, NotificationItem } from "@/components/coach";
import { Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Notification } from "@/lib/types";

export default function NotificationsPage() {
  const { refreshMe } = useAuth();
  const { data } = useSWR<Notification[]>("/me/notifications?limit=100");

  useEffect(() => {
    const unread = data?.filter((n) => !n.read).map((n) => n.id) ?? [];
    if (unread.length) {
      api("/me/notifications/read", { method: "POST", json: { ids: unread } }).then(() => refreshMe());
    }
  }, [data, refreshMe]);

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Murabbiy xabarlari" subtitle="Yutuqlaringiz, eslatmalar va qo'llab-quvvatlash — hammasi shu yerda." />
      <Card>
        <div className="mb-4 flex items-center gap-3">
          <CoachAvatar />
          <p className="text-sm text-mist">Men har kuni siz bilanman. Yiqilsangiz — turishga yordam beraman. 🤝</p>
        </div>
        {!data && [0, 1, 2, 3].map((i) => <Skeleton key={i} className="mb-2 h-16" />)}
        {data?.length === 0 && <EmptyState icon="💬" title="Hali xabar yo'q" body="Challenge boshlang — birinchi xabarim darhol keladi." />}
        <div className="flex flex-col gap-2">
          {data?.map((item, i) => <NotificationItem key={item.id} item={item} index={Math.min(i, 8)} />)}
        </div>
      </Card>
    </div>
  );
}
