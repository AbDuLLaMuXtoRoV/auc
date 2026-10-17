import { notFound } from "next/navigation"

import { PublicProfile } from "@/components/profile/public-profile"

export const metadata = {
  title: "Sotuvchi reytingi — Bazart",
}

export default async function UserProfilePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const userId = Number(id)
  if (!Number.isInteger(userId) || userId <= 0) notFound()

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
      <PublicProfile userId={userId} />
    </div>
  )
}
