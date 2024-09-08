"use client"; // Marking this as a client component

import Link from "next/link";

const Navbar = () => {
  return (
    <nav className="bg-gray-900 shadow-lg py-4">
      <div className="container mx-auto px-4 flex justify-between items-center">
        <div className="text-xl font-bold text-white">pip-ai</div>
        <div className="md:flex space-x-8">
          <button onClick={() => alert("Chill we aren't there yet")}>
            <span className="bg-blue-500 text-white px-4 py-2 rounded-full hover:bg-blue-600 transition duration-300 cursor-pointer">
              Log In
            </span>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
