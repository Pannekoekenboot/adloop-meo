// Tiny class-name joiner — keeps JSX readable without pulling in clsx.
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
