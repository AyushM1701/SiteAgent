import React from "react";import {createRoot} from "react-dom/client";import "./base.css";
import Hero from "./src/components/Hero";
import Capabilities from "./src/components/Capabilities";
import Architecture from "./src/components/Architecture";
import Questions from "./src/components/Questions";
import Footer from "./src/components/Footer";
createRoot(document.getElementById("root")!).render(<><a className="skip" href="#main">Skip to content</a><main id="main"><Hero/><Capabilities/><Architecture/><Questions/><Footer/></main></>);