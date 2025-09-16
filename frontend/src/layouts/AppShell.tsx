import BottomTab from "../components/BottomTab";
import { Outlet } from "react-router-dom";


export default function AppShell() {
  return (
    <div className="min-h-screen bg-app">
      {/* container responsivo  relative para ancorar FAB e etc */}
      <div className="relative mx-auto w-full px-4 sm:px-6 lg:px-8
                      max-w-screen-md md:max-w-screen-lg lg:max-w-screen-xl">
        <Outlet />
        {/* bottom tab visível em todas as telas */}
        <BottomTab />
      </div>
    </div>
  );
}