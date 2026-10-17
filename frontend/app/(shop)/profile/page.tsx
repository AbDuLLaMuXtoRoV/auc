import { ProfileView } from "@/components/profile/profile-view"

export const metadata = {
  title: "Profil — Bazart",
}

export default function ProfilePage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
      <ProfileView />
    </div>
  )
}
