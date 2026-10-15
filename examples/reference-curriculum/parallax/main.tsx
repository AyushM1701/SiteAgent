import React from "react";import {createRoot} from "react-dom/client";import "./base.css";
import Hero from "./src/components/Hero";
import Services from "./src/components/Services";
import Projects from "./src/components/Projects";
import Contact from "./src/components/Contact";
import Footer from "./src/components/Footer";
createRoot(document.getElementById("root")!).render(<><a className="skip" href="#main">Skip to content</a><main id="main"><Hero/><Services/><Projects/><Contact/><Footer/></main></>);