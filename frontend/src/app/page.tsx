"use client";

import { motion } from "motion/react";
import { ArrowRight, BrainCircuit, Camera, Gift, HandHeart, ShieldCheck, Trophy, Users } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";

import { Logo } from "@/components/AppShell";
import { Badge, Button, Card, StreakFlame } from "@/components/ui";
import { useAuth, useFeatures } from "@/lib/auth";
import { CATEGORY, minutes } from "@/lib/format";
import type { Challenge } from "@/lib/types";

const FEATURES = [
  { icon: BrainCircuit, title: "AI shaxsiy reja", body: "Maqsad va bo'sh vaqtingizni ayting — reja vaqtingizning 80% idan oshmaydi." },
  { icon: Camera, title: "Isbot bilan odat", body: "Har kuni rasm yoki matn. AI tekshiradi, kunlik kod aldashga yo'l qo'ymaydi." },
  { icon: ShieldCheck, title: "O'zingizga garov", body: "Xohlasangiz pul qo'ying — bajarsangiz 100% qaytadi. Pul hech qachon faqat AI qarori bilan kuymaydi." },
  { icon: HandHeart, title: "Murabbiy yoningizda", body: "Yutuqda tabriklaydi, qiyin kunda qo'llab-quvvatlaydi, kechqurun eslatadi." },
  { icon: Users, title: "Tengdoshlar reytingi", body: "O'z yoshingiz va hududingizdagilar bilan haftalik bellashuv." },
  { icon: Trophy, title: "Streak va ballar", body: "Uzluksiz kunlar ko'proq ball beradi. Freeze — kasal kunlar uchun." },
];

const STEPS = ["Maqsadni ayting", "Rejani tasdiqlang", "Har kuni isbot", "G'alaba 🏆"];

function CatalogPreview() {
  const { data } = useSWR<Challenge[]>("/challenges");
  if (!data?.length) return null;
  return (
    <section className="mx-auto max-w-6xl px-5 py-20">
      <h2 className="font-display text-3xl font-bold">Tayyor challenge'lar</h2>
      <p className="mt-2 text-mist">Yoki AI bilan o'zingizga moslab tuzing.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {data.slice(0, 8).map((c) => {
          const meta = CATEGORY[c.category];
          const Icon = meta.icon;
          return (
            <Card key={c.id} className="flex flex-col gap-3 p-5">
              <div className={`grid size-11 place-items-center rounded-2xl bg-gradient-to-br ${meta.gradient}`}>
                <Icon className="size-5" />
              </div>
              <p className="font-semibold">{c.title}</p>
              <div className="mt-auto flex flex-wrap gap-1.5">
                <Badge>{c.duration_days} kun</Badge>
                <Badge>{minutes(c.minutes_per_week)}/hafta</Badge>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

export default function Landing() {
  const { token } = useAuth();
  const { stakesEnabled } = useFeatures();
  const features = FEATURES.map((f) =>
    f.icon === ShieldCheck && !stakesEnabled
      ? { icon: Gift, title: "Hammasi bepul", body: "Reja, isbot, murabbiy va reyting — barchasi bepul. Faqat boshlash kerak." }
      : f,
  );
  const cta = token ? { href: "/dashboard", label: "Davom etish" } : { href: "/register", label: "Bepul boshlash" };

  return (
    <div className="overflow-x-clip">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <div className="flex items-center gap-2">
          {!token && (
            <Button href="/login" variant="ghost" size="sm">
              Kirish
            </Button>
          )}
          <Button href={cta.href} size="sm">
            {cta.label}
          </Button>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pt-10 pb-20 lg:grid-cols-[1.1fr_1fr] lg:pt-20">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <Badge className="border-flame-500/30 bg-flame-500/10 text-flame-300">🔥 Odatlar platformasi · 7 yoshdan</Badge>
          <h1 className="mt-6 font-display text-4xl leading-[1.08] font-bold sm:text-6xl">
            O'zingga bergan <span className="text-flame">va'dangni</span> bajar.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-mist">
            Maqsadingizni ayting — AI reja tuzadi. Har kuni isbot yuboring, streak'ingizni o'stiring va tengdoshlaringiz bilan
            bellashing. Qiyin kunlarda murabbiy yoningizda.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button href={cta.href} size="lg">
              {cta.label} <ArrowRight className="size-5" />
            </Button>
            <Button href="#qanday" variant="secondary" size="lg">
              Qanday ishlaydi?
            </Button>
          </div>
        </motion.div>

        <div className="relative mx-auto h-[420px] w-full max-w-md">
          <div className="bg-flame absolute inset-10 rounded-full opacity-25 blur-3xl" />
          <Card className="animate-float absolute top-0 left-0 w-64 [--tilt:-4deg]">
            <p className="text-sm text-mist">Joriy streak</p>
            <div className="mt-2">
              <StreakFlame streak={21} size="lg" />
            </div>
            <p className="mt-3 text-sm text-white/80">21 kunlik sport — oxirgi hafta!</p>
          </Card>
          <Card className="animate-float absolute top-36 right-0 w-72 [--tilt:3deg] [animation-delay:-2s]">
            <p className="text-xs font-semibold tracking-widest text-flame-400 uppercase">Murabbiy</p>
            <p className="mt-2 font-semibold">Siz buni uddaladingiz 🔥</p>
            <p className="mt-1 text-sm text-white/75">14 kun ketma-ket! Maqsadga 7 ish kuni qoldi.</p>
          </Card>
          <Card className="animate-float absolute bottom-0 left-8 w-60 [--tilt:-2deg] [animation-delay:-4s]">
            <p className="text-sm text-mist">2008-yilda tug'ilganlar</p>
            <p className="mt-1 font-display text-3xl font-bold">
              #3 <span className="text-base font-medium text-mint">↑ 5</span>
            </p>
          </Card>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-12">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, body }, i) => (
            <motion.div key={title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.06 }}>
              <Card className="h-full">
                <Icon className="size-7 text-flame-400" />
                <h3 className="mt-4 font-display text-lg font-semibold">{title}</h3>
                <p className="mt-2 leading-relaxed text-mist">{body}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      <section id="qanday" className="mx-auto max-w-6xl px-5 py-20">
        <h2 className="text-center font-display text-3xl font-bold">4 qadam — va odat sizniki</h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-4">
          {STEPS.map((step, i) => (
            <div key={step} className="glass rounded-3xl p-6 text-center">
              <div className="bg-flame mx-auto grid size-12 place-items-center rounded-2xl font-display text-lg font-bold">{i + 1}</div>
              <p className="mt-4 font-semibold">{step}</p>
            </div>
          ))}
        </div>
      </section>

      <CatalogPreview />

      <section className="mx-auto max-w-4xl px-5 py-20 text-center">
        <Card className="relative overflow-hidden px-6 py-14">
          <div className="bg-flame absolute -top-24 left-1/2 size-72 -translate-x-1/2 rounded-full opacity-25 blur-3xl" />
          <h2 className="relative font-display text-3xl font-bold sm:text-4xl">
            Mukammal kunni kutmang — <span className="text-flame">bugunni</span> mukammal qiling.
          </h2>
          <Button href={cta.href} size="lg" className="relative mt-8">
            {cta.label} <ArrowRight className="size-5" />
          </Button>
        </Card>
      </section>

      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 pb-10 text-sm text-mist">
        <span>© {new Date().getFullYear()} PIT — Personal Improvement Together</span>
        <nav className="flex gap-5">
          <Link href="/terms" className="hover:text-white">
            Foydalanish shartlari
          </Link>
          <Link href="/privacy" className="hover:text-white">
            Maxfiylik siyosati
          </Link>
        </nav>
      </footer>
    </div>
  );
}
