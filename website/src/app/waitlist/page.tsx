"use client"
import { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
export default function Waitlist() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();

    // Simple email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setMessage('Please enter a valid email address.');
      return;
    }

    // Here, you would typically send the email to your server or a service like Mailchimp
    // For this example, we'll just simulate a successful submission
    setIsSubmitted(true);
    setMessage('Thank you! You have been added to the waitlist.');
    setEmail(''); // Clear the input field after submission
  };

  return (
    <div className="bg-gray-900 text-gray-100 min-h-screen flex flex-col items-center justify-center">
      <Head>
        <title>Join the Waitlist</title>
        <meta name="description" content="Submit your email to join the waitlist for our upcoming product." />
        <link rel="icon" href="/favicon.ico" />
      </Head>
    
      <main className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold mb-6 text-center text-white">Join Our Waitlist</h1>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 text-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          {message && (
            <p className={`text-sm ${isSubmitted ? 'text-green-500' : 'text-red-500'} mb-4`}>
              {message}
            </p>
          )}
          <button
            type="submit"
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-300"
          >
            Join the Waitlist
          </button>
        </form>
      </main>
    </div>
  );
}
