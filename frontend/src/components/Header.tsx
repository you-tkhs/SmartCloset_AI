import Link from "next/link";
import { ClosetIcon, SparklesIcon, UploadIcon } from "@/components/icons";

const NAV_ITEMS = [
  { href: "/", label: "クローゼット", icon: ClosetIcon },
  { href: "/upload", label: "衣服を登録", icon: UploadIcon },
  { href: "/suggest", label: "コーデ提案", icon: SparklesIcon },
];

export function Header() {
  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mx-auto flex w-full max-w-5xl items-center gap-6 px-6 py-3">
        <Link href="/" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          SmartCloset AI
        </Link>
        <nav className="flex gap-4">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-1.5 text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
