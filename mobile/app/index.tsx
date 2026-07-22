import { Redirect } from 'expo-router';

// The app opens on the Explore tab. This root route makes the site root
// (index.html) resolve for static web hosting instead of 404-ing.
export default function Index() {
  return <Redirect href="/explore" />;
}
