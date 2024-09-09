"use client"
import Head from 'next/head';
import GifDisplay from './components/GifDisplay'; // Ensure the path to GifDisplay is correct
import Link from 'next/link';
import Image from 'next/image';
import imgPath from '../../public/assets/grimrepor.png';

export default function Home() {
  return (
    <>
    <Head>
      <title>Grim-Repo</title>
      <meta name="description" content="Support our AI-driven version control project." />
      <link rel="icon" href="/favicon.ico" />
    </Head>
      
    <div className="bg-gray-900 text-gray-100">

      {/* Hero Section */}
      <section className="bg-gray-800 py-16 shadow-lg">
        <div className="container mx-auto px-4 text-center">
          <Image
            src={imgPath}
            alt={"Grim Repor"}
            width={300}
            height={300}
            className="rounded-lg shadow-lg mx-auto pb-4"
            quality={100} // Ensures the image quality is high
          />

          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Grim-Repor:
          </h1>
          <h3 className="text-2xl md:text-5xl font-bold text-white mb-6">
            Just fixed your <s><i>dead</i></s> dependencies 
          </h3>          
          <p className="text-lg md:text-xl text-gray-300 mb-6 max-w-[60vw] mx-auto">
We've built an AI agent framwork that finds great research papers with code with broken-version python dependencies and makes sure that your code compiles for your users!          </p>
<div className="bg-gray-900 text-green-400 font-mono text-lg md:text-xl py-4 px-6 rounded-lg mb-6 inline-block shadow-md cursor-pointer">
  <span className="text-blue-400">you are here because </span> we found your broken <span className="text-gray-100">&lt;repo&gt;</span>
  <svg
    onClick={() => {
      const command = "grimrepo fix <your_repo_here>";
      navigator.clipboard.writeText(command).then(() => {
        // Optionally, add feedback to the user here (e.g., a toast notification)
      }).catch(err => {
        console.error('Failed to copy: ', err);
      });
    }}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 32 32"
    className="inline-block ml-2 w-4 h-4 cursor-pointer hover:fill-current hover:text-blue-700 transition-colors duration-300"
  >
    <g fill="#90979c" className="color000000 svgShape" data-name="Layer 2">
      <path
        d="M28.47,11.64a2.74,2.74,0,0,0-.91-1.42L21.88,5.56A2.56,2.56,0,0,0,20.6,5a2.32,2.32,0,0,0-.5-.05h0L16,1.56A2.77,2.77,0,0,0,14.22.92h-8a2.8,2.8,0,0,0-2.8,2.8V13a1,1,0,0,0,1,1h0a1,1,0,0,0,1-1V3.71a.8.8,0,0,1,.8-.8H13.5v2H12.11a2.8,2.8,0,0,0-2.8,2.8V25.08H6.23a.8.8,0,0,1-.8-.8V20a1,1,0,0,0-1-1h0a1,1,0,0,0-1,1v4.29a2.8,2.8,0,0,0,2.8,2.8H9.31v1.2a2.8,2.8,0,0,0,2.8,2.8H25.78a2.79,2.79,0,0,0,2.79-2.79V12.38A2.52,2.52,0,0,0,28.47,11.64Zm-7.09-3.9,3.84,3.15H21.71a.33.33,0,0,1-.33-.33Zm-5.88-4,1.44,1.18H15.5ZM25.78,29.08H12.11a.8.8,0,0,1-.8-.8V7.71a.8.8,0,0,1,.8-.8h7.27v3.64a2.33,2.33,0,0,0,2.33,2.33h4.86v15.4A.79.79,0,0,1,25.78,29.08Z"
        className="color000000 svgShape"
      />
      <path
        d="M23 16H16a1 1 0 1 0 0 2h7a1 1 0 0 0 0-2zM23 22.38H16a1 1 0 1 0 0 2h7a1 1 0 0 0 0-2z"
        className="color000000 svgShape"
      />
    </g>
  </svg>
</div>



        </div>
        <div className='flex justify-center mt-6'>
        <Link href="/waitlist">
            <span className="bg-blue-500 text-white px-6 py-3 rounded-full hover:bg-blue-600 transition duration-300 cursor-pointer shadow-lg">
              Give us a new repo to fix
            </span>
          </Link>
        </div>
         
      </section>
      {/* GIF Section */}
      <section className="bg-gray-700 py-20 shadow-lg">
        <div className="container mx-auto  text-center mt-[-2rem]">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
We Keep Great Code Alive          </h1>        <p className="text-lg md:text-xl text-gray-300 max-w-[60vw] mb-6 mx-auto">
          Time goes by and dependencies break. But maintenance is dull. We allow researchers to focus on what they do best: science.
                    </p>
          <GifDisplay altText="Funny GIF" width={400} height={300} />
        </div>
      </section>


 {/* About Section */}
 <section className="py-16 bg-gray-900 shadow-md">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-6">Our Commitment</h2>
          <p className="text-lg text-gray-400 max-w-[60vw] mx-auto mb-6">
            We are a group of developers who have faced the frustration of incompatible dependencies in GitHub repositories for years. Our mission is to create an AI-driven tool to solve this issue for everyone.
          </p>
        </div>

        <div className="flex justify-center space-x-4">
      <a
        href="https://venmo.com/Connor-Dirks-1"
        target="_blank"
        rel="noopener noreferrer"
        className="bg-green-500 text-white px-4 py-3 rounded-full hover:bg-green-600 transition duration-300 shadow-lg"
      >
        THANKS TIP! $10
      </a>

      <a
        href="https://calendly.com/sundaiclub/pip-ai-let-s-talk-about-the-pain-of-broken-repos" // Replace with your actual Calendly link
        target="_blank"
        rel="noopener noreferrer"
        className="bg-blue-500 text-white px-6 py-3 rounded-full hover:bg-blue-600 transition duration-300 shadow-lg"
      >
        Talk - Interview
      </a>

      <a
        href="https://tally.so/r/3XEKKV" // Replace with your actual Twitter (X) link
        target="_blank"
        rel="noopener noreferrer"
        className="bg-gray-500 text-white px-6 py-3 rounded-full hover:bg-gray-600 transition duration-300 shadow-lg"
      >
        Give us a new repo to fix
      </a>
    </div>
      </section>


      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8 shadow-lg">
        <div className="container mx-auto px-4 text-center">
          <p>&copy; 2024 AI Version Control. All rights reserved.</p>
        </div>
      </footer>
    </div>
    </>
  );
}
