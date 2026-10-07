from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from app.db import ROOT, pool, query, query_many, transaction
from app.security import password_hash


def rows_one(sql, params=(), conn=None):
    rows = query(sql, params, conn)
    return rows[0] if rows else None


CATEGORIES = [
    ("Python","python","Terminal"),("Java","java","Coffee"),("JavaScript","javascript","Braces"),("HTML & CSS","html-css","PanelsTopLeft"),
    ("Web Development","web-development","Globe2"),("Full Stack Development","full-stack","Layers3"),("Data Science","data-science","ChartNoAxesCombined"),
    ("Artificial Intelligence","artificial-intelligence","BrainCircuit"),("Machine Learning","machine-learning","Workflow"),("Generative AI","generative-ai","Sparkles"),
    ("DevOps","devops","GitBranch"),("Cloud Computing","cloud","Cloud"),("Cyber Security","cyber-security","ShieldCheck"),("Data Analytics","data-analytics","ChartColumnIncreasing"),
    ("UI/UX","ui-ux","Figma"),("Aptitude","aptitude","Lightbulb"),("Interview Preparation","interview-prep","MessagesSquare"),("Government Exam Preparation","government-exams","Landmark"),
]
INSTRUCTORS = [
    ("Ananya Rao","Senior Software Engineer","Hyderabad","Makes complex ideas feel practical."),("Rohan Mehta","Data Scientist","Mumbai","Builds data products for high-growth teams."),
    ("Priya Nair","Product Designer","Bengaluru","Designs inclusive digital experiences."),("Arjun Kulkarni","Cloud Architect","Pune","Helps teams ship reliably at scale."),
    ("Kavya Iyer","AI Researcher","Chennai","Works at the intersection of language and AI."),("Kabir Sethi","Security Consultant","Delhi","Makes security a habit, not a checklist."),
    ("Meera Shah","Full Stack Developer","Ahmedabad","Enjoys teaching by building real products."),("Ishaan Das","Engineering Lead","Kolkata","Mentors early-career developers."),
    ("Sana Khan","Career Coach","Jaipur","Helps people prepare for their next role."),("Devendra Joshi","Competitive Exam Faculty","Indore","Turns practice into measurable progress."),
]
COURSES = [
    ("python-fundamentals","Python Fundamentals: From Zero to Projects","Write your first useful programs and learn to think in Python.","python","Beginner",18,499,999,0,True),
    ("modern-javascript","Modern JavaScript Essentials","From the language basics to asynchronous code and browser APIs.","javascript","Beginner",14,599,1299,2,True),
    ("full-stack-react-node","Full Stack Web Development with React & Node","Build and ship a production-ready web app end to end.","full-stack","Intermediate",42,1499,2999,6,True),
    ("sql-data-analytics","SQL & Data Analytics","Turn real datasets into answers teams can act on.","data-analytics","Beginner",16,699,1499,1,True),
    ("ai-for-everyday-work","Practical Generative AI for Work","Use modern AI tools thoughtfully in everyday workflows.","generative-ai","Beginner",10,799,1599,4,True),
    ("machine-learning-starter","Machine Learning: A Practical Starter","Train, evaluate and explain your first machine learning models.","machine-learning","Intermediate",28,1299,2499,8,True),
    ("cloud-devops-foundations","Cloud & DevOps Foundations","Understand cloud basics, containers, CI/CD and deployment.","devops","Beginner",22,999,1999,3,False),
    ("java-interview-prep","Java Programming & Interview Prep","Strengthen your Java fundamentals and problem-solving skills.","java","Intermediate",24,899,1799,7,False),
    ("html-css-responsive","Responsive Web Design with HTML & CSS","Create accessible layouts that work beautifully on every screen.","html-css","Beginner",12,449,999,6,False),
    ("cybersecurity-basics","Cyber Security Essentials","Learn how to identify common threats and reduce risk.","cyber-security","Beginner",15,699,1499,5,False),
    ("python-data-science","Python for Data Science","Explore, clean and visualise data with Python.","data-science","Intermediate",26,1199,2299,1,True),
    ("ux-ui-portfolio","UI/UX Design: Research to Portfolio","Take an idea from user research through a polished prototype.","ui-ux","Beginner",20,999,1999,2,False),
    ("cloud-aws-starter","Cloud Computing for Beginners","Learn core cloud concepts through practical examples.","cloud","Beginner",17,799,1599,3,False),
    ("aptitude-placement-ready","Quantitative Aptitude for Placements","Practise the patterns that appear in campus assessments.","aptitude","Beginner",14,399,899,9,False),
    ("interview-confidence","Interview Skills for Your First Role","Prepare your stories, portfolio and technical interview routine.","interview-prep","Beginner",8,499,999,8,True),
    ("ai-machine-learning","AI & Machine Learning in Practice","Connect modern AI concepts with useful, small projects.","artificial-intelligence","Intermediate",30,1399,2799,4,False),
    ("full-stack-python","Full Stack Python with Django","Build a complete web product with Python and Django.","full-stack","Intermediate",36,1499,2999,0,False),
    ("devops-kubernetes","Docker & Kubernetes for Developers","Package and orchestrate applications with confidence.","devops","Advanced",24,1299,2499,3,False),
    ("government-exam-reasoning","Reasoning Skills for Government Exams","Build speed and accuracy through structured practice.","government-exams","Beginner",16,399,899,9,False),
    ("data-structures-java","Data Structures & Algorithms with Java","Learn core data structures and build a steady practice habit.","java","Intermediate",32,1099,2199,7,False),
]
FIELD_TEST_TITLES = {
    "Aptitude": [
        "Algorithmic Problem Solving",
        "Number Algorithms in Python",
        "Arithmetic Calculation Code",
        "Loop and Counting Problems",
        "Array Logic Challenges",
        "Sorting and Searching Code",
        "Probability Simulation Code",
        "Recursion and Backtracking",
        "Time Complexity Practice",
        "Algorithm Coding Challenge",
    ],
    "Artificial Intelligence": [
        "AI Programming Foundations",
        "Search Algorithms in Code",
        "Knowledge Graph Programming",
        "Machine Learning APIs",
        "Neural Network Implementation",
        "Deep Learning Workflows",
        "NLP Programming",
        "Computer Vision Code",
        "Generative AI API Integration",
        "AI Coding Challenge",
    ],
    "Cloud Computing": [
        "Cloud SDK Programming",
        "Serverless Function Code",
        "Cloud Storage APIs",
        "Infrastructure as Code",
        "IAM Policy Programming",
        "Container Service Deployment",
        "Cloud Networking Configuration",
        "Scalable Service Patterns",
        "Cloud Automation Scripts",
        "Cloud Coding Challenge",
    ],
    "Cyber Security": [
        "Secure Coding Foundations",
        "Input Validation Code",
        "Authentication Implementation",
        "Password Hashing Code",
        "SQL Injection Prevention",
        "Web Security Headers",
        "Authorization Checks",
        "Secret Management Code",
        "Security Testing Workflows",
        "Cyber Security Coding Challenge",
    ],
    "Data Analytics": [
        "Python Analytics Foundations",
        "Pandas Data Cleaning",
        "SQL Query Programming",
        "NumPy Data Operations",
        "Analytics Pipeline Code",
        "Data Visualization Code",
        "Exploratory Analysis Scripts",
        "Statistical Computing",
        "Regression with Python",
        "Analytics Coding Challenge",
    ],
    "Interview Preparation": [
        "Coding Interview Foundations",
        "Arrays and Strings Problems",
        "Data Structures in Code",
        "Algorithm Design Practice",
        "SQL Coding Questions",
        "Object-Oriented Design Code",
        "Debugging Interview Problems",
        "API Implementation Exercises",
        "Code Review Scenarios",
        "Technical Interview Coding Challenge",
    ],
    "Python": [
        "Python Programming Foundations",
        "Control Flow Coding",
        "Data Structures in Python",
        "Functions & Scope",
        "File Handling",
        "OOP in Python",
        "Libraries & Modules",
        "Error Handling",
        "Comprehensions & Iteration",
        "Python Coding Challenge",
    ],
    "Java": [
        "Java Core Programming",
        "Object-Oriented Java Code",
        "Collections & Maps",
        "Exceptions & Debugging",
        "Inheritance & Interfaces",
        "Streams & Lambda Expressions",
        "Concurrency Programming",
        "Memory & JVM Fundamentals",
        "Java API & Libraries",
        "Java Coding Challenge",
    ],
    "JavaScript": [
        "JavaScript Programming Foundations",
        "Functions & Scope",
        "Arrays & Objects",
        "Async JavaScript",
        "Promises & Fetch",
        "DOM & Events",
        "Closures & Hoisting",
        "ES Modules & APIs",
        "Debugging & Patterns",
        "JavaScript Coding Challenge",
    ],
    "HTML & CSS": [
        "Semantic HTML Programming",
        "CSS Selectors and Box Model",
        "Layout Implementation Code",
        "Flexbox & Grid Programming",
        "Form Markup & Validation",
        "Responsive CSS Programming",
        "Typography and Styling Code",
        "Accessible Markup",
        "CSS Animation Code",
        "HTML/CSS Coding Challenge",
    ],
    "Web Development": [
        "Web Programming Foundations",
        "HTTP Handler Implementation",
        "Frontend Component Code",
        "State & Data Flow",
        "Security & Authentication",
        "Performance & Debugging",
        "Testing & Quality",
        "Caching & Networking",
        "Deployment Scripting",
        "Web Development Coding Challenge",
    ],
    "Full Stack Development": [
        "Full Stack Programming",
        "Frontend and Backend Code",
        "REST API Implementation",
        "Database Query Programming",
        "Authentication and Session Code",
        "State Management Implementation",
        "Deployment Pipeline Configuration",
        "Error Handling and Logging Code",
        "Performance and Scalability Code",
        "Full Stack Coding Challenge",
    ],
    "Data Science": [
        "Python Data Science Foundations",
        "Data Cleaning with Pandas",
        "Exploratory Analysis Code",
        "Statistics Libraries in Python",
        "Visualization Programming",
        "Feature Engineering Code",
        "Model Evaluation Code",
        "Regression Implementation",
        "Probability Simulation Code",
        "Data Science Coding Challenge",
    ],
    "Machine Learning": [
        "Machine Learning Programming",
        "Supervised Learning Code",
        "Classification Metrics",
        "Regression Models",
        "Feature Engineering",
        "Cross Validation",
        "Bias & Variance",
        "Clustering Concepts",
        "Model Deployment Code",
        "Machine Learning Coding Challenge",
    ],
    "Generative AI": [
        "LLM API Programming",
        "Prompt Construction Code",
        "Model Response Parsing",
        "Retrieval Pipeline Code",
        "LLM Safety Checks",
        "Evaluation Code",
        "Fine-Tuning Workflows",
        "AI Integration Patterns",
        "Responsible AI Implementation",
        "Generative AI Coding Challenge",
    ],
    "DevOps": [
        "Developer Git Workflows",
        "CI Pipeline Configuration",
        "Dockerfile Programming",
        "Container Automation",
        "Infrastructure as Code",
        "Monitoring and Logging Scripts",
        "Network Configuration Code",
        "Release Pipeline Automation",
        "Cloud Operations Scripts",
        "DevOps Coding Challenge",
    ],
    "UI/UX": [
        "Semantic Component Programming",
        "CSS Layout Implementation",
        "Responsive Interface Code",
        "Accessible Component Code",
        "JavaScript Interaction Code",
        "Design System Components",
        "Form Validation UX",
        "Reusable UI Components",
        "Frontend Testing Code",
        "UI/UX Coding Challenge",
    ],
    "Government Exam Preparation": [
        "Programming Logic Foundations",
        "Number Series Algorithms",
        "Coding-Decoding Programs",
        "Loop-Based Reasoning",
        "Array Pattern Programs",
        "Conditional Logic Problems",
        "Data Sufficiency Algorithms",
        "String Processing Code",
        "Timed Coding Problems",
        "Government Exam Coding Challenge",
    ],
}

FIELD_TEST_DESCRIPTIONS = {
    category: [
        f"Practise {category.lower()} through short programming and code-reading problems.",
        f"Build working code while practising focused {category.lower()} concepts.",
        f"Apply {category.lower()} ideas in algorithms, code, and debugging tasks.",
        f"Strengthen {category.lower()} skills by tracing and improving code.",
        f"Solve practical programming prompts based on {category.lower()}.",
        f"Test your {category.lower()} knowledge with intermediate coding problems.",
        f"Use reusable code patterns to solve more nuanced {category.lower()} tasks.",
        f"Apply {category.lower()} concepts to realistic software scenarios.",
        f"Tackle advanced {category.lower()} programming and code-review questions.",
        f"Finish with a coding challenge covering the core {category.lower()} syllabus.",
    ]
    for category in FIELD_TEST_TITLES
}

TOPIC_BANK = {
    "Aptitude": ["Algorithmic reasoning","Number algorithms","Arithmetic in code","Loops and counting","Arrays","Sorting","Searching","Recursion","Complexity analysis","Probability simulation","Input parsing","Coding interview problems"],
    "Artificial Intelligence": ["Python AI APIs","Search algorithms","Knowledge graphs","Training pipelines","Neural network code","Tensor operations","NLP preprocessing","Computer vision APIs","Model inference","Prompt APIs","AI evaluation code","Responsible AI checks"],
    "Cloud Computing": ["Cloud SDKs","Serverless functions","Storage APIs","Infrastructure as code","IAM policies","Container deployment","Cloud networking","Scalable services","Cloud automation","Environment configuration","Cloud logging","Deployment scripts"],
    "Cyber Security": ["Secure coding","Input validation","Authentication code","Password hashing","SQL injection prevention","Web security headers","Authorization checks","Secret handling","Dependency scanning","Cryptography APIs","Security tests","Incident automation"],
    "Data Analytics": ["Python analytics","Pandas cleaning","SQL queries","NumPy operations","ETL programming","Chart code","Exploratory analysis","Statistics in Python","Data validation","Regression code","Notebook workflows","Analytics automation"],
    "Interview Preparation": ["Algorithm implementation","Array problems","String processing","Data structures","SQL coding","Object-oriented design","Debugging","API implementation","Unit testing","Code review","Complexity analysis","Technical problem solving"],
    "Python": ["Variables and expressions","Control flow","Lists","Dictionaries","Strings","Functions","Modules","File handling","Exceptions","Classes","Iterators","Comprehensions"],
    "Java": ["Java expressions","Control flow","Arrays and collections","Maps and sets","Methods","Classes and objects","Inheritance","Interfaces","Exceptions","Generics","Streams","Unit testing"],
    "JavaScript": ["JavaScript expressions","Functions","Scope","Objects","Arrays","Async and await","DOM code","Events","Closures","Modules","Promises","Error handling"],
    "HTML & CSS": ["Semantic HTML code","CSS selectors","Box model","Flexbox code","Grid layouts","Form markup","Responsive CSS","Accessible markup","Typography styles","Pseudo-classes","CSS animations","CSS variables"],
    "Web Development": ["HTTP handlers","Frontend components","API clients","Routing code","State management","Authentication middleware","Caching code","Performance profiling","Automated tests","Web security","Deployment scripts","Accessible interfaces"],
    "Full Stack Development": ["Frontend components","Backend APIs","Routing","Database queries","Authentication","Session handling","Caching","Deployment pipelines","Logging","Integration tests","Performance","Scalable services"],
    "Data Science": ["Python data cleaning","Exploratory analysis code","Statistics libraries","Visualization code","Probability simulation","Feature engineering","Regression implementation","Classification code","Hypothesis tests","Data pipelines","Model evaluation","Notebook programming"],
    "Machine Learning": ["Model training code","Classification","Regression","Overfitting prevention","Cross-validation code","Feature scaling","Bias and variance","Clustering","Evaluation metrics","Regularization","Feature selection","Model deployment"],
    "Generative AI": ["LLM API calls","Prompt construction","Response parsing","Transformer libraries","Retrieval code","Embeddings","RAG pipelines","Hallucination checks","Safety filters","Model evaluation","Fine-tuning scripts","AI workflow integration"],
    "DevOps": ["Git commands","CI configuration","Container code","Dockerfiles","Infrastructure as code","Monitoring scripts","Logging","Network configuration","Security automation","Release pipelines","Environment variables","Deployment automation"],
    "UI/UX": ["Semantic components","CSS layouts","Responsive interfaces","Accessible controls","JavaScript interactions","Design system components","Form validation","Reusable components","Frontend tests","Visual state code","Interactive prototypes","UI performance"],
    "Government Exam Preparation": ["Number algorithms","Coding-decoding programs","Loop reasoning","Array patterns","Conditional logic","String algorithms","Data structure problems","Sorting and searching","Input parsing","Algorithm tracing","Complexity basics","Timed coding problems"],
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def build_field_test_catalog() -> list[tuple[str, str, str, str]]:
    catalog: list[tuple[str, str, str, str]] = []
    for category_name, _, _ in CATEGORIES:
        titles = FIELD_TEST_TITLES.get(category_name, [f"{category_name} Test {i}" for i in range(1, 11)])
        descriptions = FIELD_TEST_DESCRIPTIONS.get(category_name, [f"Practice {category_name.lower()} concepts." for _ in range(10)])
        for index, (title, description) in enumerate(zip(titles, descriptions), start=1):
            catalog.append((f"{slugify(category_name)}-test-{index:02d}", title, category_name, description))
    return catalog


def generate_question(category_name: str, test_index: int, q_index: int, topic: str) -> tuple[str, str, str, list[str], str]:
    base = (test_index + 1) * 17 + q_index * 13 + len(category_name)
    if category_name == "Aptitude":
        if topic == "Number System":
            a = base + 11; b = base + 17
            prompt = f"If {a} is divided by {b}, what is the remainder?"
            answer = str(a % b)
            distractors = [str((a + 3) % b), str((a + 5) % b), str((a + 9) % b)]
            explanation = f"The remainder is the result of {a} modulo {b}, which is {answer}."
        elif topic == "Percentages":
            original = 750 + base * 2
            discount = 15 + (q_index % 5) * 5
            price = int(original * (100 - discount) / 100)
            prompt = f"A product priced at ₹{original} is discounted by {discount}%. What is the sale price?"
            answer = f"₹{price}"
            distractors = [f"₹{int(original * (100 - discount / 2) / 100)}", f"₹{int(original * (100 - discount * 2) / 100)}", f"₹{int(original * (100 - discount / 4) / 100)}"]
            explanation = f"A {discount}% discount reduces the price to {discount/100:.0%} of the original, giving ₹{price}."
        elif topic == "Profit & Loss":
            cost = 440 + base * 3
            profit = 18 + (q_index % 6) * 2
            selling = int(cost * (100 + profit) / 100)
            prompt = f"A shopkeeper buys an item for ₹{cost} and sells it at a {profit}% profit. What is the selling price?"
            answer = f"₹{selling}"
            distractors = [f"₹{int(cost * (100 + profit / 2) / 100)}", f"₹{int(cost * (100 + profit * 2) / 100)}", f"₹{int(cost * (100 + profit / 3) / 100)}"]
            explanation = f"Selling price = cost × (1 + profit/100), so it becomes ₹{selling}."
        else:
            value = 24 + (base % 18)
            prompt = f"A train covers {value * 12} km in {value} hours. What is its average speed in km/h?"
            answer = str((value * 12) // value)
            distractors = [str((value * 12) // (value - 1)), str((value * 12) // (value + 1)), str((value * 12) // max(1, value - 2))]
            explanation = f"Average speed = total distance / total time = {value * 12} / {value} = {answer} km/h."
    elif category_name == "Artificial Intelligence":
        if topic == "AI fundamentals":
            prompt = "Which statement best describes an AI system that learns patterns from data without being explicitly programmed for each rule?"
            answer = "It uses data-driven learning to generalize from examples"
            distractors = ["It only follows fixed if-then instructions", "It cannot respond to new inputs", "It ignores historical data"]
            explanation = "Machine learning and broader AI approaches learn patterns from data and apply them to new situations."
        elif topic == "Search algorithms":
            prompt = "In a shortest-path problem, which search approach is most appropriate when edge costs vary and the best route is unknown initially?"
            answer = "A* or Dijkstra-style shortest-path search"
            distractors = ["A single fixed rule-based lookup", "Only DFS with no cost tracking", "A pure random walk"]
            explanation = "Weighted pathfinding needs cost-aware search such as Dijkstra or A*."
        else:
            prompt = f"Which concept is most directly associated with {topic}?"
            answer = f"A practical method used in {category_name.lower()} workflows"
            distractors = ["A random browser-only artifact", "A database schema only", "A hardware-only instruction set"]
            explanation = f"{topic} is a core concept in modern {category_name.lower()} practice and decision-making."
    elif category_name == "Cloud Computing":
        if topic == "IaaS, PaaS, SaaS":
            prompt = "Which cloud service model gives you managed application software that you access over the network without managing the underlying infrastructure?"
            answer = "SaaS"
            distractors = ["IaaS", "PaaS only for storage", "Private networking only"]
            explanation = "SaaS delivers a complete application service as a managed offering."
        elif topic == "Containers":
            prompt = "Why are containers useful in cloud workloads?"
            answer = "They package an application and its dependencies consistently across environments"
            distractors = ["They eliminate the need for operating systems", "They replace all networking setup", "They store only static HTML files"]
            explanation = "Containers encourage consistent runs by bundling code and dependencies together."
        else:
            prompt = f"Which option best matches {topic} in cloud operations?"
            answer = "A core capability that supports reliability, scale, or secure delivery"
            distractors = ["A browser only feature", "A permanent local file lock", "A UI-only design pattern"]
            explanation = f"{topic} is a core operational concept used to run workloads reliably in the cloud."
    elif category_name == "Cyber Security":
        if topic == "CIA triad":
            prompt = "Which security goal is most directly protected when data is prevented from unauthorized disclosure?"
            answer = "Confidentiality"
            distractors = ["Availability", "Integrity", "Usability"]
            explanation = "Confidentiality ensures that information is only accessible to authorized users."
        elif topic == "Authentication":
            prompt = "What is multi-factor authentication designed to reduce?"
            answer = "The risk of password-only compromise"
            distractors = ["The need for backups", "The need for network cables", "The cost of developer laptops"]
            explanation = "MFA increases assurance by requiring an additional factor beyond a password."
        else:
            prompt = f"Which answer best explains the role of {topic} in a secure system?"
            answer = "It reduces attack surface and improves defensive control"
            distractors = ["It removes the need for logging", "It disables all network traffic", "It only affects UI styling"]
            explanation = f"{topic} is a security control or concept that helps build safer systems."
    elif category_name == "Data Analytics":
        if topic == "SQL":
            prompt = "Which SQL clause is used to filter rows after grouping has happened?"
            answer = "HAVING"
            distractors = ["WHERE", "ORDER BY", "LIMIT"]
            explanation = "HAVING filters aggregated results after the GROUP BY step."
        elif topic == "Statistics":
            prompt = "Which metric is most useful for understanding the typical value in a skewed dataset?"
            answer = "Median"
            distractors = ["Mode only", "Range only", "Maximum value"]
            explanation = "Median is more robust to outliers than the mean in skewed data."
        else:
            prompt = f"Which statement best reflects the purpose of {topic} in analytics work?"
            answer = "It transforms raw data into usable insights for decisions"
            distractors = ["It removes the need for plotting data", "It creates code without evidence", "It is only relevant to UI design"]
            explanation = f"{topic} helps analysts turn messy raw information into useful and reliable decisions."
    elif category_name == "Interview Preparation":
        if topic == "Technical interview":
            prompt = "What is the strongest way to answer a technical question in an interview?"
            answer = "Explain the approach, walk through the reasoning, and test assumptions"
            distractors = ["Only provide the final answer", "Avoid examples and summarize vaguely", "Change the question to a different topic"]
            explanation = "A clear reasoning process shows depth and helps the interviewer understand your thinking."
        elif topic == "HR interview":
            prompt = "What is the best way to respond when asked about a challenge you faced at work?"
            answer = "Describe the situation, actions taken, and what you learned"
            distractors = ["Answer with only a complaint", "Say you have no challenges", "Avoid talking about teamwork"]
            explanation = "Structured STAR-style answers show maturity and reflection."
        else:
            prompt = f"Which response best demonstrates readiness for {topic}?"
            answer = "A clear, evidence-based answer that shows practical experience and learning"
            distractors = ["A vague answer with no examples", "A refusal to discuss details", "A long unrelated story"]
            explanation = f"{topic} is most effectively answered with examples and clear reasoning."
    elif category_name == "Python":
        if topic == "Dictionaries":
            prompt = "What does data.get('key', 'fallback') return when 'key' is missing?"
            answer = "'fallback'"
            distractors = ["None", "An empty list", "A KeyError"]
            explanation = "The default value is returned when the key is absent."
        elif topic == "Functions":
            prompt = "What does a function return when it reaches the end without a return statement?"
            answer = "None"
            distractors = ["0", "False", "An empty tuple"]
            explanation = "Python functions return None implicitly when no explicit return is reached."
        else:
            prompt = f"Which choice best matches the concept of {topic} in Python?"
            answer = "A core Python idea that supports reliable and readable code"
            distractors = ["A CSS rule", "A random browser event", "A database table name"]
            explanation = f"{topic} is a foundational Python concept used in real applications."
    elif category_name == "Java":
        if topic == "Collections":
            prompt = "Which Java collection is most appropriate when you need fast random access by index?"
            answer = "ArrayList"
            distractors = ["HashSet", "TreeMap", "LinkedHashSet"]
            explanation = "ArrayList provides indexed storage with efficient positional access."
        elif topic == "Inheritance":
            prompt = "Which keyword is used for a class to inherit from another class in Java?"
            answer = "extends"
            distractors = ["implements", "inherits", "super"]
            explanation = "The extends keyword creates a subclass relationship in Java."
        else:
            prompt = f"Which option best represents {topic} in Java development?"
            answer = "A standard Java concept used in production-ready code"
            distractors = ["A CSS declaration", "A serverless database only", "A browser-only idea"]
            explanation = f"{topic} is one of the building blocks of Java application design."
    elif category_name == "JavaScript":
        if topic == "Async/await":
            prompt = "What does await do inside an async function?"
            answer = "It pauses the async function until a promise resolves"
            distractors = ["It runs the function synchronously", "It cancels the promise", "It blocks all network requests"]
            explanation = "await waits for a promise and resumes execution after the value becomes available."
        elif topic == "Promises":
            prompt = "What is the main purpose of a Promise in JavaScript?"
            answer = "To represent an eventual value or failure from asynchronous work"
            distractors = ["To style a DOM element", "To replace the HTML parser", "To define a CSS layout"]
            explanation = "Promises handle asynchronous work in a structured and composable way."
        else:
            prompt = f"Which answer best captures the idea of {topic} in JavaScript?"
            answer = "A practical language feature used in real browser and server code"
            distractors = ["A database migration command", "A CSS animation layer", "A server-only file format"]
            explanation = f"{topic} is a central concept in modern JavaScript development."
    elif category_name == "HTML & CSS":
        if topic == "Flexbox":
            prompt = "Which CSS layout system is most suitable for arranging items in a row or column with flexible spacing?"
            answer = "Flexbox"
            distractors = ["CSS Grid only", "Canvas only", "Inline JavaScript"]
            explanation = "Flexbox is designed for one-dimensional layout alignment and distribution."
        elif topic == "Accessibility":
            prompt = "Why is semantic HTML important for accessibility?"
            answer = "It gives assistive technologies meaningful structure and context"
            distractors = ["It removes the need for styles", "It increases only visual contrast", "It disables screen readers"]
            explanation = "Semantic elements help screen readers and browsers understand document structure."
        else:
            prompt = f"Which answer best describes {topic} in frontend design?"
            answer = "A core HTML or CSS concept that improves structure, layout, or usability"
            distractors = ["A database management command", "A cloud storage method only", "A server hardware setting"]
            explanation = f"{topic} is a foundational piece of practical browser interface design."
    elif category_name == "Web Development":
        if topic == "HTTP":
            prompt = "Which HTTP method is typically used when a client wants to create a new resource?"
            answer = "POST"
            distractors = ["GET", "DELETE", "PATCH only"]
            explanation = "POST is commonly used to submit new data and create a resource."
        elif topic == "Security":
            prompt = "Why should sensitive data not be exposed in client-side code?"
            answer = "Clients can inspect and alter the code or values shown to them"
            distractors = ["The browser automatically secures everything", "It is impossible to read JavaScript", "It makes the API slower"]
            explanation = "Any client-side code can be inspected and manipulated, so secrets must stay on the server."
        else:
            prompt = f"What is the most relevant role of {topic} in web application development?"
            answer = "It supports reliable delivery, interaction, or security in a product"
            distractors = ["It only impacts static image files", "It disables all APIs", "It is unrelated to software design"]
            explanation = f"{topic} is a core part of building maintainable web experiences."
    elif category_name == "Full Stack Development":
        if topic == "REST API Design":
            prompt = "What is the main benefit of using clear REST resource paths?"
            answer = "They make APIs predictable and easier to understand"
            distractors = ["They prevent all need for documentation", "They remove the need for databases", "They guarantee zero latency"]
            explanation = "Good resource naming helps both developers and clients reason about API behavior."
        elif topic == "Authentication":
            prompt = "Why are sessions or tokens usually required for protected routes?"
            answer = "They let the server verify the identity of the current user"
            distractors = ["They replace all database tables", "They are only needed for CSS files", "They make every request public"]
            explanation = "Authentication is how the server decides which actions are permitted."
        else:
            prompt = f"Which answer best fits {topic} in full stack engineering?"
            answer = "A practical system concern that supports product reliability and usability"
            distractors = ["A file extension issue only", "A browser-only concept with no backend impact", "A random text formatting rule"]
            explanation = f"{topic} is an important building block in end-to-end product development."
    elif category_name == "Data Science":
        if topic == "Feature engineering":
            prompt = "Why is feature engineering important in a machine learning pipeline?"
            answer = "It converts raw data into representations that models can learn from better"
            distractors = ["It removes the need to validate models", "It makes every model identical", "It prevents all data errors"]
            explanation = "Useful features often improve model quality more than algorithm choice alone."
        elif topic == "Model evaluation":
            prompt = "Why do data science teams use validation data?"
            answer = "To estimate how the model will perform on unseen data"
            distractors = ["To avoid writing reports", "To disable all data cleaning", "To replace documentation"]
            explanation = "Validation helps judge real-world generalization beyond the training set."
        else:
            prompt = f"Which statement best describes a key role of {topic} in data science?"
            answer = "It helps convert raw data into evidence-driven business understanding"
            distractors = ["It replaces every business decision", "It makes data collection unnecessary", "It is only used for visual design"]
            explanation = f"{topic} supports reliable analysis and decision support."
    elif category_name == "Machine Learning":
        if topic == "Cross-validation":
            prompt = "Why is cross-validation commonly used in model evaluation?"
            answer = "It gives a more stable estimate of performance than one train-test split"
            distractors = ["It hides all errors from the model", "It removes the need for features", "It always guarantees the best model"]
            explanation = "Cross-validation reduces variance in performance estimates by using multiple splits."
        elif topic == "Bias & Variance":
            prompt = "Which issue is most commonly associated with an overfit model?"
            answer = "High variance and poor generalization to new data"
            distractors = ["Very low accuracy on training data", "No use of labels at all", "Perfect fairness across all samples"]
            explanation = "Overfit models fit noise or idiosyncrasies in training data rather than general patterns."
        else:
            prompt = f"Which answer best explains the concept of {topic} in machine learning?"
            answer = "A fundamental learning or evaluation idea for building reliable predictive models"
            distractors = ["A browser-only display setting", "A security-only checklist", "A database indexing method"]
            explanation = f"{topic} matters because it influences model quality, complexity, and performance."
    elif category_name == "Generative AI":
        if topic == "Prompting":
            prompt = "What is the main advantage of a well-structured prompt?"
            answer = "It gives the model clear context and expected output"
            distractors = ["It removes every model limitation", "It replaces all software tests", "It deletes training data"]
            explanation = "Prompt design influences model focus, relevance, and output quality."
        elif topic == "RAG":
            prompt = "What does retrieval-augmented generation mainly improve?"
            answer = "Grounding responses in relevant source material before answering"
            distractors = ["It reduces all need for internet access", "It ensures every answer is factually certain", "It changes the model's training data"]
            explanation = "RAG adds external context to a generation flow to improve factual grounding."
        else:
            prompt = f"Which answer best captures the relevance of {topic} in modern generative AI systems?"
            answer = "A practical design concept that improves quality, safety, or usefulness"
            distractors = ["A CSS-only behavior", "A type of HTTP status code", "An unrelated spreadsheet formula"]
            explanation = f"{topic} is one of the core ideas shaping current generative AI workflows and safeguards."
    elif category_name == "DevOps":
        if topic == "CI/CD":
            prompt = "What is a primary goal of a CI/CD pipeline?"
            answer = "Automate validation and delivery of changes to a product"
            distractors = ["Remove the need for version control", "Store every build artifact locally forever", "Disable testing altogether"]
            explanation = "CI/CD shortens feedback loops and reduces manual deployment risk."
        elif topic == "Monitoring":
            prompt = "Why do teams monitor logs and metrics in production?"
            answer = "To detect issues and understand system health before users report failures"
            distractors = ["To replace all backups", "To remove the need for source code", "To guarantee zero traffic peaks"]
            explanation = "Operational visibility helps teams respond faster to incidents and regressions."
        else:
            prompt = f"Which statement best describes the role of {topic} in DevOps practice?"
            answer = "A workflow or automation concept that improves delivery and reliability"
            distractors = ["A UI-only animation rule", "A database normalization method only", "A browser routing feature"]
            explanation = f"{topic} is a fundamental operational practice in modern software delivery."
    elif category_name == "UI/UX":
        if topic == "User research":
            prompt = "Why is user research important before designing a product experience?"
            answer = "It reveals actual user needs, pain points, and behavior"
            distractors = ["It removes the need for testing", "It guarantees a perfect design", "It only matters for marketing teams"]
            explanation = "Research helps designers solve the right problem instead of designing by assumption."
        elif topic == "Accessibility":
            prompt = "What does accessible design mainly aim to improve?"
            answer = "Inclusive usability for people with different needs and abilities"
            distractors = ["Only page loading speed", "Only color contrast", "Only mobile device choices"]
            explanation = "Accessibility is broader than color contrast and includes structure, interaction, and content clarity."
        else:
            prompt = f"Which answer best describes the purpose of {topic} in UI/UX work?"
            answer = "It helps create understandable, useful, and engaging experiences"
            distractors = ["It is only a backend concern", "It prevents all testing", "It replaces product strategy"]
            explanation = f"{topic} is part of creating experiences that users can understand and trust."
    elif category_name == "Government Exam Preparation":
        if topic == "Number series":
            prompt = "Find the next number in the series: 3, 6, 12, 24, ?"
            answer = "48"
            distractors = ["30", "36", "42"]
            explanation = "Each number is doubled, so 24 × 2 = 48."
        elif topic == "Coding-decoding":
            prompt = "If in a code language A = 1, B = 2, and C = 3, what is the code for BCA?"
            answer = "2 3 1"
            distractors = ["1 2 3", "3 2 1", "2 1 3"]
            explanation = "BCA maps directly to 2, 3, 1 in the same order."
        else:
            prompt = f"Which option best reflects the logical idea behind {topic}?"
            answer = "A reasoning pattern that can be solved systematically with evidence"
            distractors = ["A random guess", "A grammar-only rule", "A file system decision"]
            explanation = f"{topic} is a structured reasoning skill used in exam preparation and analytical thinking."
    else:
        prompt = f"Which statement best captures the value of {topic} in {category_name}?"
        answer = "It supports practical understanding, quality, and decision-making"
        distractors = ["It is unused and decorative", "It only applies to naming files", "It does not affect real work"]
        explanation = f"{topic} is a relevant and useful work concept in {category_name}."
    return topic, prompt, answer, distractors, explanation


def generate_programming_question(category_name: str, test_index: int, q_index: int, topic: str) -> tuple[str, str, str, list[str], str]:
    base = (test_index + 1) * 17 + q_index * 13 + len(category_name)
    value = base % 10 + 3
    task = q_index % 12
    context = f"{topic} ({category_name})"

    if task == 0:
        answer = str(value * 2 + 1)
        prompt = f"While coding {context}, what does this Python snippet print?\nvalue = {value}\nprint(value * 2 + 1)"
        distractors = [str(value + 1), str(value * 2), str(value * value)]
        explanation = f"The expression multiplies {value} by 2 and adds 1, producing {answer}."
    elif task == 1:
        values = [value, value + 1, value + 2]
        answer = str([item for item in values if item % 2 == 0])
        prompt = f"For {context}, what list does this Python comprehension create?\nvalues = {values}\n[item for item in values if item % 2 == 0]"
        distractors = [str(values), str([item for item in values if item % 2]), str(values[1:])]
        explanation = "The comprehension keeps only values whose remainder after division by 2 is zero."
    elif task == 2:
        answer = "0"
        prompt = f"In code for {context}, what does this expression return?\nsettings = {{'limit': {value}}}\nsettings.get('missing', 0)"
        distractors = ["None", str(value), "KeyError"]
        explanation = "dict.get returns the supplied default when the key is missing."
    elif task == 3:
        answer = str(value * 2 + 1)
        prompt = f"While implementing {context}, what does this function print?\ndef combine(a, b):\n    return a + b\nprint(combine({value}, {value + 1}))"
        distractors = [str(value), str(value + 1), str(value * 2)]
        explanation = "The function returns the sum of its two arguments."
    elif task == 4:
        answer = str(value)
        prompt = f"For {context}, how many times does this loop run?\ncount = 0\nfor item in range({value}):\n    count += 1"
        distractors = [str(value - 1), str(value + 1), str(value * 2)]
        explanation = "range(value) yields value items, from zero through value minus one."
    elif task == 5:
        answer = str(value)
        prompt = f"When writing {context}, what does this code print?\nvalues = [{value + 2}, {value}, {value + 1}]\nprint(sorted(values)[0])"
        distractors = [str(value + 1), str(value + 2), "0"]
        explanation = "sorted returns the values in ascending order, so the first item is the minimum."
    elif task == 6:
        answer = "even" if value % 2 == 0 else "odd"
        prompt = f"For a {context} program, what does this condition print?\nnumber = {value}\nprint('even' if number % 2 == 0 else 'odd')"
        distractors = ["even" if answer == "odd" else "odd", "true", "0"]
        explanation = f"{value} is {answer}, based on whether its remainder when divided by 2 is zero."
    elif task == 7:
        answer = "True"
        prompt = f"In an algorithm for {context}, what does this membership check return?\nitems = set(range({value}))\n({value - 1}) in items"
        distractors = ["False", "None", str(value)]
        explanation = "range(value) includes value - 1, and set membership returns True for a present item."
    elif task == 8:
        answer = "None"
        prompt = f"What does this Python statement return while implementing {context}?\nvalues = [{value}, {value + 1}]\nvalues.sort()"
        distractors = ["The sorted list", str(value), "True"]
        explanation = "list.sort changes the list in place and returns None."
    elif task == 9:
        answer = "The ValueError is caught and result becomes 0"
        prompt = f"In {context}, what happens when raw is 'abc'?\ntry:\n    result = int('abc')\nexcept ValueError:\n    result = 0"
        distractors = ["The exception is ignored and result is 'abc'", "A KeyError is raised", "The program always returns None"]
        explanation = "int cannot parse 'abc', so ValueError is caught and the handler assigns zero."
    elif task == 10:
        answer = "It checks that the function returns the expected value"
        prompt = f"What does this unit test verify for {context}?\nassert calculate({value}) == {value + 1}"
        distractors = ["It changes calculate's return value", "It runs calculate only in production", "It skips the comparison"]
        explanation = "assert fails if the expression is false, so this checks the expected result."
    else:
        answer = "SELECT * FROM records WHERE id = %s"
        prompt = f"Which parameterized SQL query should the program use for {context}?\ncursor.execute(query, (record_id,))"
        distractors = ["SELECT * FROM records WHERE id = '" + str(value) + "'", "SELECT * FROM records WHERE id = %s" % value, "SELECT * FROM records WHERE id = '" + str(value) + "' OR '1'='1'"]
        explanation = "A parameter placeholder keeps data separate from SQL syntax and prevents injection."

    return topic, prompt, answer, distractors, explanation


def build_question_bank_for_test(category_name: str, test_index: int) -> list[tuple[str, str, str, list[str], str]]:
    topics = TOPIC_BANK.get(category_name, [category_name])
    questions: list[tuple[str, str, str, list[str], str]] = []
    generator = generate_programming_question if category_name in TOPIC_BANK else generate_question
    for q_index in range(12):
        topic = topics[(test_index + q_index) % len(topics)]
        questions.append(generator(category_name, test_index, q_index, topic))
    return questions


MAX_ATTEMPTS = 10
PROMPTS = [
    ("Which statement best describes a variable?","A named reference to a value","A loop that runs forever","A database table","A network protocol"),
    ("What is the main purpose of a function?","To package reusable behaviour","To style a page","To store every program value","To connect to the internet"),
    ("Which approach usually makes code easier to maintain?","Use clear names and small focused units","Put all logic in one long function","Duplicate logic when possible","Avoid comments in every case"),
    ("What does an automated test help a team do?","Check expected behaviour consistently","Replace all code review","Guarantee zero defects","Remove the need for documentation"),
    ("Why should input be validated on the server?","Client input can be changed or bypassed","Browsers cannot display forms","It makes CSS load faster","It removes the need for a database"),
    ("Which is a useful first step when debugging?","Reproduce the issue and inspect the evidence","Rewrite the whole application","Ignore the error message","Disable every validation rule"),
    ("What does an API commonly provide?","A defined way for software to exchange data","A visual design file","A password hash algorithm only","A browser rendering engine"),
    ("Why is version control useful?","It records and coordinates changes over time","It automatically writes requirements","It encrypts every database","It replaces backups completely"),
    ("What is a database index designed to improve?","Finding matching rows efficiently","Making every write free","Changing a table into an API","Compressing all images"),
    ("Which practice helps protect user passwords?","Store a salted, slow password hash","Save them in plain text","Email passwords to admins","Use one shared password for all users"),
    ("What does responsive design aim to do?","Adapt a layout to different screen sizes","Make each page use more animations","Hide navigation on every screen","Load only on desktop"),
    ("What is a good way to present a result?","Explain the outcome and the next useful step","Show an unexplained number only","Hide errors from the user","Use jargon wherever possible"),
]
LEGACY_PROMPTS = [prompt[0] for prompt in PROMPTS]

# Each item is (topic, prompt, correct answer, three distractors, explanation).
# Seeded questions have stable keys so re-running the seed does not rewrite the
# content of a question already referenced by a learner's test attempt.
QUESTION_BANKS = {
    "python-basics-check": [
        ("Lists", "What does list.append(value) do?", "Adds value to the end of the list", ["Sorts the list", "Removes the last item", "Converts the list to a tuple"], "append adds one item at the end of a list."),
        ("Ranges", "Which values are produced by list(range(4))?", "0, 1, 2, 3", ["1, 2, 3, 4", "0, 1, 2, 3, 4", "4 only"], "The stop value in range is excluded."),
        ("Dictionaries", "What does settings.get('theme') return when the key is missing and no default is given?", "None", ["An empty string", "False", "A KeyError"], "dict.get returns None for a missing key unless a default is supplied."),
        ("Tuples", "Which statement about a tuple is correct?", "Its items cannot be reassigned after creation", ["It can only contain numbers", "It always removes duplicate values", "It is sorted automatically"], "Tuples are immutable containers."),
        ("Comparisons", "Which operator checks whether two Python values are equal?", "==", ["=", "!=", "is not"], "The double-equals operator compares values for equality."),
        ("Files", "Why use 'with open(path) as file:' when reading a file?", "The file is closed automatically when the block ends", ["The file is converted to JSON", "The file can only be read once", "It skips permission checks"], "A context manager closes the file even if an error occurs."),
        ("Comprehensions", "What does [n * n for n in numbers] create?", "A new list containing the square of each number", ["A dictionary of number counts", "A generator that changes numbers in place", "A sorted copy of numbers"], "The comprehension evaluates n*n for each item and builds a list."),
        ("Exceptions", "What exception is raised by looking up a missing dictionary key with data[key]?", "KeyError", ["IndexError", "ValueError", "TypeError"], "A missing key accessed with brackets raises KeyError."),
        ("Mutability", "If two variables refer to the same list, what can happen after items.append(x)?", "Both variables see the changed list", ["Only the second variable changes", "Python creates a copy automatically", "The list becomes immutable"], "Both names refer to the same mutable list object."),
        ("Built-ins", "What does len({'a': 1, 'b': 2}) return?", "2", ["1", "3", "The number of characters in the keys"], "len on a dictionary counts its keys."),
        ("Functions", "What does a function return when it reaches its end without a return statement?", "None", ["0", "An empty list", "The last local variable"], "Python functions return None by default."),
        ("Exceptions", "Which block handles a matching exception raised inside a try block?", "except", ["finally", "with", "assert"], "An except clause handles the selected exception type."),
    ],
    "javascript-core-test": [
        ("Bindings", "What does const prevent in JavaScript?", "Reassigning the variable binding", ["Changing properties of every object it references", "Calling a function stored in the variable", "Reading the variable"], "const prevents rebinding; referenced objects may still be mutable."),
        ("Equality", "What does 5 === '5' evaluate to?", "false", ["true", "5", "undefined"], "Strict equality does not coerce a number into a string."),
        ("Arrays", "What does scores.map(score => score * 2) return?", "A new array with each score doubled", ["The first doubled score only", "The original array sorted", "A boolean for each score"], "map transforms every item into a new array."),
        ("Arrays", "Which method returns only array items that pass a condition?", "filter", ["reduce", "push", "join"], "filter keeps items whose callback returns true."),
        ("Scope", "Where is a let variable declared inside a pair of braces available?", "Only inside that block", ["Across the entire application", "Only inside the next function call", "Only in the browser console"], "let is block-scoped."),
        ("Types", "Which expression reliably checks that value is an array?", "Array.isArray(value)", ["typeof value === 'array'", "value instanceof JSON", "value.isList()"], "Array.isArray is the built-in array check."),
        ("Promises", "When does the callback passed to promise.then run?", "When the promise fulfills", ["Before the promise starts", "Only when the promise rejects", "Every time the page renders"], "then handles a fulfilled promise; catch handles rejection."),
        ("Async", "What does an async function always return?", "A Promise", ["A callback", "A DOM node", "A synchronous iterator"], "JavaScript wraps an async function result in a Promise."),
        ("Optional chaining", "What does user.profile?.city do if profile is null?", "It evaluates to undefined without throwing", ["It throws a TypeError", "It creates an empty profile", "It returns false"], "Optional chaining stops the property access when the left side is nullish."),
        ("JSON", "What does JSON.parse(text) do?", "Converts JSON text into a JavaScript value", ["Converts any JavaScript function into JSON", "Sends JSON to a server", "Escapes HTML in a string"], "JSON.parse reads valid JSON text into JavaScript data."),
        ("Nullish values", "When does value ?? fallback use fallback?", "When value is null or undefined", ["Whenever value is zero", "Whenever value is an empty string", "Whenever value is false"], "The nullish coalescing operator checks only null and undefined."),
        ("Spread syntax", "What does [...first, ...second] make when both values are arrays?", "A new array containing items from both arrays", ["A set of unique items", "A string joining both arrays", "A reference to first only"], "Array spread copies the items into a new array."),
    ],
    "web-fundamentals": [
        ("Semantic HTML", "Which element is the best choice for an action a user can activate?", "<button>", ["<span>", "<div>", "<section>"], "A button provides native keyboard and action semantics."),
        ("Forms", "How should a visible label be connected to an input with id='email'?", "Set the label's for attribute to email", ["Give the label the same name as the form", "Put the label inside a script element", "Set the input's alt attribute to email"], "The label for value matches the input id."),
        ("Accessibility", "What should useful image alt text describe?", "The image's relevant meaning or information", ["The image file's folder path", "Every pixel color", "The CSS class used to display it"], "Alt text conveys the information an image adds to the page."),
        ("HTTP status", "What does HTTP status 404 indicate?", "The requested resource was not found", ["The request succeeded and created a resource", "The user is authenticated", "The server has permanently shut down"], "404 means the requested resource could not be found."),
        ("HTTP methods", "Which HTTP method is normally used to retrieve a resource?", "GET", ["PATCH", "DELETE", "CONNECT"], "GET requests a representation of a resource."),
        ("HTTPS", "What does HTTPS add to HTTP for a browser connection?", "TLS encryption and server identity verification", ["Automatic database backups", "A guarantee that the website content is honest", "A faster CPU"], "TLS protects data in transit and helps authenticate the server."),
        ("Responsive CSS", "What is a CSS media query commonly used for?", "Applying styles when viewport or device conditions match", ["Sending a form to a server", "Changing a database schema", "Creating a JavaScript promise"], "Media queries let layouts adapt to screen conditions."),
        ("DOM", "What is the DOM in a browser?", "A tree representation of the document that scripts can inspect and update", ["A network protocol for images", "A CSS color format", "A server-side database"], "The browser exposes page structure through the Document Object Model."),
        ("Viewport", "Why include a viewport meta tag on a responsive page?", "So mobile browsers use the device width for the layout viewport", ["To encrypt browser cookies", "To enable JavaScript modules", "To resize every image file"], "The viewport declaration helps the page use the device's actual width."),
        ("Forms", "What does a form's action attribute specify?", "The URL that receives the form submission", ["The CSS layout of its fields", "The input's validation message", "The browser's history limit"], "action identifies the submission endpoint."),
        ("HTTP status", "Which status code commonly signals that a resource was created successfully?", "201", ["301", "401", "503"], "201 Created confirms a resource was created."),
        ("Script loading", "What does the defer attribute do for a classic external script?", "Runs it after HTML parsing while preserving document order", ["Runs it before the HTML is downloaded", "Blocks all images from loading", "Moves the script to the server"], "Deferred scripts run after parsing and keep their order."),
    ],
    "sql-foundations": [
        ("SELECT", "Which SQL clause chooses which columns appear in a result?", "SELECT", ["WHERE", "ORDER BY", "COMMIT"], "SELECT names the output columns or expressions."),
        ("Filtering", "Which clause filters rows before they are returned?", "WHERE", ["GROUP BY", "VALUES", "GRANT"], "WHERE keeps rows that satisfy a condition."),
        ("Joins", "What does an INNER JOIN return?", "Rows with matching join values in both tables", ["Every possible row pair", "Only unmatched rows from the left table", "All rows from either table whether matched or not"], "An inner join keeps matching rows from both sides."),
        ("Aggregation", "Which clause groups rows so aggregates can be calculated per group?", "GROUP BY", ["LIMIT", "DISTINCT", "OFFSET"], "GROUP BY forms groups used by aggregate functions."),
        ("Aggregation", "What does COUNT(*) count?", "Rows in the selected group or result", ["Only columns named id", "Distinct values in every column", "Bytes used by the table"], "COUNT(*) counts rows, including rows with null fields."),
        ("Keys", "What is the purpose of a primary key?", "Uniquely identify each row in a table", ["Sort all query results automatically", "Encrypt the table", "Allow duplicate identifiers"], "A primary key uniquely identifies a record."),
        ("Relationships", "What does a foreign key normally enforce?", "A reference to a valid row in another table", ["A column contains only unique values", "A query always uses an index", "A table has no null values"], "Foreign keys maintain referential integrity."),
        ("NULL", "How should SQL test whether city has no value?", "city IS NULL", ["city = NULL", "city == None", "city EQUALS EMPTY"], "NULL is checked with IS NULL, not ordinary equality."),
        ("Sorting", "How do you request newest records first when created_at stores a timestamp?", "ORDER BY created_at DESC", ["GROUP BY created_at ASC", "WHERE created_at NEWEST", "SORT created_at FIRST"], "DESC orders from later timestamps to earlier ones."),
        ("Parameterization", "Why use placeholders for values in a SQL query?", "To keep user input separate from SQL syntax", ["To disable database constraints", "To make every query a transaction", "To convert strings into column names"], "Parameterized queries help prevent SQL injection and handle values safely."),
        ("Transactions", "What does COMMIT do in a transaction?", "Makes the transaction's changes permanent", ["Cancels all changes in the transaction", "Creates a foreign key", "Locks the database forever"], "COMMIT saves the transaction's successful changes."),
        ("Indexes", "What is a common trade-off of adding an index?", "Reads may get faster while writes and storage cost more", ["Reads and writes both become free", "The table can no longer contain nulls", "The index removes duplicate rows automatically"], "Indexes use storage and must be maintained during writes."),
    ],
    "aptitude-practice": [
        ("Percentages", "What is 15% of 200?", "30", ["15", "25", "35"], "0.15 multiplied by 200 equals 30."),
        ("Ratios", "A mixture has milk and water in the ratio 2:3 and totals 25 litres. How much is milk?", "10 litres", ["5 litres", "15 litres", "20 litres"], "There are five total parts, so each part is 5 litres."),
        ("Averages", "What is the average of 6, 8 and 10?", "8", ["6", "9", "24"], "The sum 24 divided by 3 is 8."),
        ("Speed and distance", "A vehicle travels at 60 km/h for 2.5 hours. How far does it travel?", "150 km", ["120 km", "140 km", "180 km"], "Distance equals speed multiplied by time: 60 × 2.5."),
        ("Profit and loss", "An item costs ₹500 and sells for ₹600. What is the profit percentage on cost?", "20%", ["10%", "16.7%", "25%"], "Profit is ₹100; 100 divided by 500 is 20%."),
        ("Simple interest", "What simple interest accrues on ₹2,000 at 5% per year for 2 years?", "₹200", ["₹100", "₹150", "₹250"], "Simple interest is principal × rate × time: 2000 × .05 × 2."),
        ("Work rates", "A worker completes a job in 10 days at a constant rate. What fraction of the job is completed in one day?", "1/10", ["1/5", "1/9", "10"], "One day's work is the reciprocal of the 10-day total."),
        ("Number patterns", "What comes next in 2, 6, 12, 20, ...?", "30", ["26", "28", "32"], "The differences are 4, 6, 8, then 10."),
        ("Probability", "What is the probability of rolling an even number on a fair six-sided die?", "1/2", ["1/3", "2/3", "5/6"], "Three of the six outcomes are even."),
        ("Discounts", "A ₹800 item is discounted by 25%. What is its sale price?", "₹600", ["₹200", "₹575", "₹625"], "A 25% discount is ₹200, leaving ₹600 to pay."),
        ("Fractions", "What is 3/4 of 80?", "60", ["20", "40", "64"], "80 divided by 4 is 20; three parts equal 60."),
        ("Perimeter", "A rectangle is 8 cm long and 5 cm wide. What is its perimeter?", "26 cm", ["13 cm", "40 cm", "80 cm"], "Perimeter is 2 × (8 + 5) = 26 cm."),
    ],
    "ai-literacy-check": [
        ("Language models", "What does a large language model primarily learn to do?", "Predict likely next tokens from context", ["Look up every answer in a live database", "Prove every generated statement is true", "Execute code without any input"], "Next-token prediction is a core training objective for language models."),
        ("Reliability", "What is a hallucination in generative AI?", "A plausible-sounding output that is unsupported or false", ["A model refusing every request", "An encrypted training example", "A verified citation"], "Fluent output can still contain invented claims."),
        ("Bias", "Why can an AI system repeat unfair patterns?", "Its data or design may reflect existing imbalances", ["It always understands social context perfectly", "Its output is selected by a random number only", "Bias is removed automatically during deployment"], "Models can reproduce patterns present in data and design choices."),
        ("Privacy", "What is a safer practice when using a public AI tool?", "Remove personal or confidential details before sharing a prompt", ["Paste customer records to improve the answer", "Share account passwords for context", "Assume prompts are always private"], "Minimizing sensitive information reduces privacy exposure."),
        ("Security", "What is prompt injection?", "Instructions in untrusted input that try to override a system's intended rules", ["A method for compressing model weights", "A way to cite a research paper", "A type of spreadsheet formula"], "Prompt injection uses untrusted content to manipulate model behavior."),
        ("Grounding", "How can retrieval-augmented generation improve a response?", "It supplies relevant source material for the model to use", ["It guarantees every response is correct", "It removes the need to check sources", "It retrains the model after every prompt"], "Retrieved context can ground an answer, but still needs verification."),
        ("Evaluation", "What makes an AI evaluation set useful?", "Examples that represent real tasks and likely failure cases", ["Only examples the model already answers correctly", "One prompt repeated many times", "Questions without expected outcomes"], "Representative tests reveal how a system performs in its intended use."),
        ("Training", "In supervised learning, what does a labeled example provide?", "An input paired with an expected target or answer", ["A network cable", "A GPU temperature reading", "A deployment password"], "Labels provide the target used to train or evaluate a model."),
        ("Overfitting", "What is overfitting?", "A model performs well on training examples but poorly on new ones", ["A model uses less memory than planned", "A prompt contains too many words", "A server scales to more machines"], "Overfit models fail to generalize beyond the training data."),
        ("Human review", "When should a high-impact AI recommendation receive human review?", "Before it drives a consequential decision", ["Only after the decision becomes irreversible", "Never if the output sounds confident", "Only when the user requests a transcript"], "Human oversight is important when errors can materially affect people."),
        ("Embeddings", "What do text embeddings represent?", "Text as numeric vectors that capture useful relationships", ["A guaranteed factual summary", "A database password", "An image's original pixels"], "Embeddings map content into vectors useful for similarity tasks."),
        ("Classification", "What does a classification model produce?", "A category or label for an input", ["A guaranteed explanation of causality", "A new database table", "A sorted list of source files"], "Classification assigns an input to one or more defined classes."),
    ],
    "cloud-basics-test": [
        ("Service models", "What does IaaS usually provide?", "Virtualized compute, storage and networking resources", ["Only a finished email application", "A programming language standard", "A physical notebook"], "IaaS provides infrastructure resources that customers configure."),
        ("Availability", "Why deploy across multiple availability zones?", "To reduce dependence on one isolated data-center location", ["To make a password unnecessary", "To remove all software bugs", "To guarantee zero network latency"], "Separate zones can improve resilience to a localized outage."),
        ("Storage", "Which storage type is commonly suited to images and backups addressed as objects?", "Object storage", ["CPU cache", "A relational index", "A process stack"], "Object storage is designed for durable, key-addressed files and blobs."),
        ("Identity", "What does least privilege mean for a cloud identity?", "Grant only the permissions needed for its task", ["Grant administrator access to every service", "Share one account among all staff", "Never rotate credentials"], "Least privilege limits the impact of mistakes or compromised credentials."),
        ("Scaling", "What does autoscaling do when configured with capacity rules?", "Adjusts resource count as demand changes", ["Renames cloud regions", "Encrypts application code", "Deletes backups after each request"], "Autoscaling adds or removes capacity based on configured signals."),
        ("Serverless", "What does serverless computing mean to an application developer?", "The provider manages much of the server provisioning and scaling", ["No servers exist anywhere", "The application cannot store data", "Every request must run on a laptop"], "Servers still run the code; the provider manages more of the infrastructure."),
        ("CDN", "What is a content delivery network mainly used for?", "Serving cached content closer to users", ["Replacing application authentication", "Writing database migrations", "Creating source-code branches"], "A CDN distributes content to edge locations to reduce delivery distance."),
        ("Networking", "What is a load balancer commonly responsible for?", "Distributing incoming requests across healthy targets", ["Converting SQL into HTML", "Storing user passwords in plain text", "Compiling every client browser"], "Load balancers route traffic among configured targets."),
        ("Observability", "Which signal most directly records discrete application events over time?", "Logs", ["A CSS stylesheet", "A container image", "A DNS suffix"], "Logs record events and diagnostic details."),
        ("Recovery", "What should a team do to know whether backups can restore service?", "Regularly test a restoration procedure", ["Assume a successful backup job guarantees recovery", "Keep the only backup on the same disk", "Disable monitoring"], "A restore test checks that backup data is usable when needed."),
        ("Regions", "What is a cloud region?", "A geographic area containing cloud infrastructure locations", ["A user's browser profile", "A programming language package", "A database column type"], "Regions are geographically distinct provider locations."),
        ("Shared responsibility", "In a managed cloud service, who remains responsible for application access settings?", "The customer configures and reviews their own access policies", ["The provider automatically knows each user's job", "The internet service provider", "No one; access settings are unnecessary"], "Providers secure the platform, while customers manage their configuration and identities."),
    ],
    "java-fundamentals": [
        ("JVM", "What does the Java Virtual Machine execute?", "Java bytecode", ["CSS selectors", "SQL table names", "Python indentation"], "Java source is compiled to bytecode that runs on a JVM."),
        ("Objects", "What does new Account() normally do when Account is a class?", "Creates an Account object and calls its constructor", ["Deletes the Account class", "Starts a database transaction", "Converts Account to an interface"], "new constructs an object using the class constructor."),
        ("Encapsulation", "Why make a field private and expose controlled methods?", "To protect internal state behind a class boundary", ["To make the field global", "To disable object creation", "To turn the field into a package"], "Encapsulation lets a class control how its state is accessed."),
        ("Interfaces", "What does a Java interface primarily define?", "A contract of methods a type can implement", ["A database connection string", "A running object instance", "A CSS layout"], "An interface declares behavior that implementing classes provide."),
        ("Collections", "What does ArrayList.add(item) do?", "Adds an item to the list", ["Sorts all items automatically", "Removes the list's first item", "Converts the list to a map"], "add appends an element to an ArrayList."),
        ("Collections", "Which call returns the number of items in an ArrayList named names?", "names.size()", ["names.length", "size(names)", "names.count"], "Java collection classes expose size()."),
        ("Modifiers", "What does final mean on a local variable after it is assigned?", "It cannot be assigned again", ["It is visible from every package", "It is deleted after one use", "It is automatically synchronized"], "A final local variable can be assigned once."),
        ("Static members", "How is a static method normally called on class Utility?", "Utility.methodName()", ["new static Utility()", "this.Utility() from any file", "Utility->methodName()"], "A static method belongs to the class rather than an instance."),
        ("Inheritance", "Which keyword declares that a class inherits from another class?", "extends", ["inherits", "instanceof", "superclass"], "A Java class uses extends to inherit from a class."),
        ("Exceptions", "What does a catch block do?", "Handles a matching exception thrown from the try block", ["Declares a new class", "Runs only when the try block succeeds", "Creates a thread"], "catch handles the exception type it declares."),
        ("Types", "Which is a Java primitive type?", "int", ["Integer", "String", "ArrayList"], "int is primitive; Integer is its wrapper class."),
        ("Strings", "What happens when Java code concatenates a String with another value?", "A new String value is produced", ["The original String object is modified", "The String becomes a primitive int", "The JVM removes the variable"], "Java String objects are immutable."),
    ],
    "cyber-safety-check": [
        ("Phishing", "Which sign should make you suspicious of an unexpected account-reset email?", "A mismatched sender domain or link destination", ["The message uses your correct first name", "The email arrives during the day", "The company logo has a green color"], "Check the actual sender and link destination before acting."),
        ("Authentication", "What does multi-factor authentication add?", "A second proof beyond the password", ["A public copy of the password", "A longer username", "An automatic software update"], "MFA requires more than one kind of evidence to sign in."),
        ("Password storage", "How should an application store user passwords?", "As salted, slow password hashes", ["As readable text in a database", "As a reversible URL parameter", "In a shared spreadsheet"], "A password hash makes a database leak less damaging."),
        ("Injection", "How do parameterized SQL queries help against SQL injection?", "They keep supplied values separate from executable SQL", ["They make every user an administrator", "They disable the database parser", "They sanitize CSS only"], "Parameters prevent input from being interpreted as query syntax."),
        ("Access control", "What is least privilege in security?", "Give an account only the access needed for its work", ["Give every account full access", "Reuse an admin account for routine tasks", "Disable access logs"], "Restricting permissions reduces the damage from misuse."),
        ("Patching", "Why apply security updates promptly?", "They can fix known vulnerabilities in software", ["They guarantee users never make mistakes", "They replace backups", "They make encryption unnecessary"], "Updates often close weaknesses that attackers already know about."),
        ("Transport security", "What does HTTPS help protect?", "Data traveling between a browser and the authenticated server", ["Data after it is copied into a public document", "A device from every type of malware", "The truthfulness of a webpage"], "HTTPS protects a connection in transit, not every endpoint or claim."),
        ("Cross-site scripting", "What is a key defense when displaying untrusted text in a web page?", "Escape or safely encode it for its output context", ["Insert it directly as executable HTML", "Store it in a CSS class", "Trust it because it came from a database"], "Context-aware encoding prevents text from becoming executable markup."),
        ("Backups", "Why keep a protected backup separate from normal writable files?", "Ransomware or an operator error may affect the primary system", ["It makes the website load faster", "It removes the need to test restores", "It lets users share passwords"], "An isolated backup can remain recoverable if the primary data is compromised."),
        ("Credential safety", "What is a benefit of using a password manager?", "It can create and store unique strong passwords", ["It makes every site use the same password", "It sends passwords to search engines", "It disables multi-factor authentication"], "Unique passwords reduce the impact of one service being breached."),
        ("CSRF", "What does a CSRF defense help prevent?", "A site being tricked into accepting an unwanted action from a signed-in browser", ["A user choosing a weak password", "A server running out of disk space", "A database query returning no rows"], "CSRF protections validate that a state-changing request was intentionally initiated."),
        ("Incident response", "What is a sensible first response to a suspected compromised account?", "Secure the account and report the incident through the approved channel", ["Delete all logs immediately", "Reuse the same password everywhere", "Ignore alerts until the next month"], "Prompt containment and reporting support investigation and recovery."),
    ],
    "interview-readiness": [
        ("Structured answers", "What does the STAR method help organize?", "Situation, Task, Action and Result in an example", ["Syntax, Testing, API and Runtime", "Salary, Title, Address and References", "Search, Type, Align and Render"], "STAR provides a clear structure for experience-based answers."),
        ("Problem solving", "What is a useful first step when a coding question is unclear?", "Ask focused questions to clarify inputs, outputs and constraints", ["Start coding without confirming the task", "Assume hidden requirements", "Decline to discuss the problem"], "Clarifying requirements prevents solving the wrong problem."),
        ("Communication", "What should you do while solving a technical interview problem?", "Explain your assumptions and reasoning as you work", ["Stay silent until time ends", "Read unrelated notes aloud", "Claim the answer is correct without checking"], "Clear reasoning helps the interviewer understand your approach."),
        ("Honesty", "If you do not know an answer, what is a constructive response?", "Say what you know, identify the gap and reason through it", ["Invent a confident-sounding fact", "Change the subject without answering", "Blame the interviewer"], "Honest reasoning shows how you handle uncertainty."),
        ("Project examples", "What makes a project explanation useful in an interview?", "Your specific contribution, decisions and outcome", ["Only the project's title", "A list of every tool you have heard of", "An unsupported claim that it was perfect"], "Specific contributions and trade-offs make an example credible."),
        ("Behavioral questions", "When asked how you handled a disagreement, what is a strong focus?", "How you listened, worked through options and reached an outcome", ["How you proved the other person was foolish", "Why you avoided the conversation", "How you took credit for the team's work"], "A balanced example shows collaboration and resolution."),
        ("Resume evidence", "How can you make a resume achievement more concrete?", "Include a relevant result or scale when you can support it", ["Add numbers you cannot verify", "Use only vague adjectives", "List responsibilities without outcomes"], "Supported measures make impact easier to understand."),
        ("Code quality", "After writing a solution in a coding interview, what should you do?", "Walk through an example and check edge cases", ["Stop immediately without review", "Assume the first version handles every input", "Remove all variable names"], "A brief walkthrough can reveal errors and show verification habits."),
        ("Questions", "What is a useful question to ask an interviewer near the end?", "How the team defines success for this role", ["Whether you can skip the role's core work", "For another candidate's private feedback", "For their account password"], "A role-focused question helps you understand expectations."),
        ("Remote interviews", "What should you do before a remote interview begins?", "Check the meeting link, audio and internet setup", ["Disable the microphone permanently", "Wait until the interview to install required software", "Share your screen with private files open"], "A short setup check reduces avoidable interruptions."),
        ("Feedback", "How should you respond to constructive feedback during an interview?", "Listen, ask a clarifying question and consider the suggestion", ["Interrupt and reject it immediately", "Pretend you did not hear it", "Argue about the interviewer's motives"], "A thoughtful response shows coachability and composure."),
        ("Follow-up", "What is an appropriate interview follow-up message?", "A brief thank-you that refers to the conversation and your interest", ["A demand for an immediate offer", "A message containing confidential data", "Repeated messages every few minutes"], "A concise, respectful follow-up reinforces interest without pressure."),
    ],
}
STUDENTS = [
    ("Aarav Sharma","Hyderabad","JNTU Hyderabad"),("Diya Patel","Ahmedabad","Nirma University"),("Vivaan Iyer","Chennai","Anna University"),
    ("Anika Reddy","Bengaluru","PES University"),("Aditya Verma","Indore","IIT Indore"),("Saanvi Mehta","Mumbai","University of Mumbai"),
    ("Reyansh Singh","Delhi","Delhi Technological University"),("Ira Kulkarni","Pune","Savitribai Phule Pune University"),
    ("Arnav Das","Kolkata","Jadavpur University"),("Myra Khan","Jaipur","MNIT Jaipur"),
]


def main():
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required. Set it in bharatlearn/.env.")
    print("Connecting to PostgreSQL...", flush=True)
    pool.open(wait=True)
    try:
        print("Connected. Applying schema and seeding catalog...", flush=True)
        query("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        schema=(ROOT/"server"/"src"/"db"/"schema.sql").read_text(encoding="utf-8")
        for statement in schema.split(";"):
            if statement.strip():
                query(statement)
        with transaction() as conn:
            for name,slug,icon in CATEGORIES:
                query("INSERT INTO categories(name,slug,icon) VALUES($1,$2,$3) ON CONFLICT(slug) DO UPDATE SET name=EXCLUDED.name,icon=EXCLUDED.icon",[name,slug,icon],conn)
            for index,(name,title,city,bio) in enumerate(INSTRUCTORS,1):
                query("INSERT INTO instructors(id,full_name,title,city,bio,rating) VALUES($1,$2,$3,$4,$5,4.8) ON CONFLICT(id) DO UPDATE SET full_name=EXCLUDED.full_name,title=EXCLUDED.title,city=EXCLUDED.city,bio=EXCLUDED.bio",[index,name,title,city,bio],conn)
            if os.getenv("SEED_DEMO_USERS", "true").strip().lower() in {"1", "true", "yes"}:
                student_hash=password_hash("Student123!")
                for index,(name,city,college) in enumerate(STUDENTS):
                    query("INSERT INTO users(full_name,email,phone,password_hash,city,college,education) VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT(email) DO NOTHING",[name,f"student{index+1}@bharatlearn.in",f"+91 90000 1000{index}",student_hash,city,college,"Undergraduate"],conn)
            admin_email=os.getenv("SEED_ADMIN_EMAIL","admin@bharatlearn.in")
            admin_hash=password_hash(os.getenv("SEED_ADMIN_PASSWORD","ChangeMe123!"))
            query("INSERT INTO users(full_name,email,password_hash,city,role) VALUES($1,$2,$3,$4,$5) ON CONFLICT(email) DO UPDATE SET role=EXCLUDED.role,password_hash=EXCLUDED.password_hash,full_name=EXCLUDED.full_name",["BharatLearn Admin",admin_email,admin_hash,"Hyderabad","admin"],conn)
            for course_index, course in enumerate(COURSES, start=1):
                course_id,title,subtitle,cat_slug,level,hours,price,original,instructor_index,featured=course
                print(f"Seeding course {course_index}/{len(COURSES)}: {title}", flush=True)
                category=rows_one("SELECT id FROM categories WHERE slug=$1",[cat_slug],conn)
                query("""INSERT INTO courses(id,title,subtitle,description,category_id,instructor_id,level,duration_hours,price_inr,original_price_inr,thumbnail_url,featured)
                  VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) ON CONFLICT(id) DO UPDATE SET title=EXCLUDED.title,subtitle=EXCLUDED.subtitle,description=EXCLUDED.description,category_id=EXCLUDED.category_id,instructor_id=EXCLUDED.instructor_id,level=EXCLUDED.level,duration_hours=EXCLUDED.duration_hours,price_inr=EXCLUDED.price_inr,original_price_inr=EXCLUDED.original_price_inr,featured=EXCLUDED.featured""",
                  [course_id,title,subtitle,f"{subtitle} Learn by doing with short lessons, practical exercises and a portfolio-ready project. Designed for learners across India, with clear explanations and a steady path from foundations to confident application.",category["id"],instructor_index+1,level,hours,price,original,None,featured],conn)
                existing=rows_one("SELECT count(*)::int AS n FROM course_modules WHERE course_id=$1",[course_id],conn)["n"]
                if not existing:
                    for module_index,module_title in enumerate(("Start with the foundations","Build something useful")):
                        module=rows_one("INSERT INTO course_modules(course_id,title,position) VALUES($1,$2,$3) RETURNING id",[course_id,module_title,module_index],conn)
                        for lesson_index,lesson_name in enumerate(("Welcome & setup","Core concepts","Guided practice")):
                            suffix=" — project lab" if module_index else ""
                            video="https://www.youtube-nocookie.com/embed/ysz5S6PUM-U" if lesson_index==0 else None
                            query("INSERT INTO lessons(module_id,title,description,video_url,duration_minutes,position) VALUES($1,$2,$3,$4,$5,$6)",[module["id"],lesson_name+suffix,f"A concise, practical lesson in {title.lower()}. Follow along, pause to practise and keep your notes nearby.",video,10+lesson_index*3,lesson_index],conn)
                        quiz=rows_one("INSERT INTO course_quizzes(module_id,title) VALUES($1,$2) RETURNING id",[module["id"],"Project lab knowledge check" if module_index else "Foundations knowledge check"],conn)
                        query("INSERT INTO quiz_questions(quiz_id,prompt,options,correct_index,explanation) VALUES($1,$2,$3,0,$4)",[quiz["id"],"What helps you make steady progress while learning?",json.dumps(["Practise each idea with a small example","Skip every exercise","Memorise without context","Wait until the end to try anything"]),"Short practice helps turn new ideas into usable skills."],conn)
            category_names = [name for name, _, _ in CATEGORIES]
            query("UPDATE tests SET is_published=false WHERE category = ANY($1)", [category_names], conn)
            query("UPDATE test_questions SET is_active=false WHERE test_id IN (SELECT id FROM tests WHERE category = ANY($1))", [category_names], conn)

            print("Preparing practice tests and batching questions by field...", flush=True)
            question_rows_by_category = {name: [] for name, _, _ in CATEGORIES}
            for test_index, (test_id, title, category, description) in enumerate(build_field_test_catalog(), start=0):
                query("""INSERT INTO tests(id,title,description,category,duration_minutes,total_marks,passing_percent,correct_marks,wrong_marks,max_attempts,question_count,leaderboard_enabled)
                  VALUES($1,$2,$3,$4,20,12,40,1,0.25,$5,12,true) ON CONFLICT(id) DO UPDATE SET title=EXCLUDED.title,description=EXCLUDED.description,category=EXCLUDED.category,max_attempts=EXCLUDED.max_attempts,question_count=EXCLUDED.question_count,is_published=true""", [test_id, title, description, category, MAX_ATTEMPTS], conn)

                for q_index, (topic, prompt, answer, distractors, explanation) in enumerate(build_question_bank_for_test(category, test_index)):
                    seed_key = f"programming-v2-{test_id}-{q_index:02d}-{slugify(topic)}"
                    options = [answer, *distractors]
                    correct_index = options.index(answer)
                    question_rows_by_category[category].append(
                        (test_id, topic, prompt, json.dumps(options), correct_index, explanation, q_index, seed_key)
                    )

            question_sql = """INSERT INTO test_questions(test_id,topic,prompt,options,correct_index,explanation,position,is_active,seed_key)
              VALUES($1,$2,$3,$4,$5,$6,$7,true,$8)
              ON CONFLICT (test_id,seed_key) WHERE seed_key IS NOT NULL
              DO UPDATE SET topic=EXCLUDED.topic,prompt=EXCLUDED.prompt,options=EXCLUDED.options,correct_index=EXCLUDED.correct_index,
                explanation=EXCLUDED.explanation,position=EXCLUDED.position,is_active=true"""
            for category_name, _, _ in CATEGORIES:
                query_many(question_sql, question_rows_by_category[category_name], conn)
                print(f"Seeded programming tests for {category_name}.", flush=True)

            for category_name, _, _ in CATEGORIES:
                count = rows_one("SELECT COUNT(*)::int AS total FROM tests WHERE category = $1 AND is_published=true", [category_name], conn)["total"]
                if count != 10:
                    raise RuntimeError(f"Expected 10 tests in {category_name}, found {count}.")
                question_total = rows_one("SELECT COUNT(*)::int AS total FROM test_questions tq JOIN tests t ON t.id = tq.test_id WHERE t.category = $1 AND t.is_published=true AND tq.is_active=true", [category_name], conn)["total"]
                if question_total != 120:
                    raise RuntimeError(f"Expected 120 questions for {category_name}, found {question_total}.")

            students=query("SELECT id FROM users WHERE role='student' ORDER BY created_at LIMIT 10",conn=conn)
            sample_progress=(17,33,50,67,83,0,33,67,50,17)
            for index,student in enumerate(students[:len(COURSES)]):
                course_id=COURSES[index][0]
                query("INSERT INTO enrollments(user_id,course_id,progress_percent) VALUES($1,$2,0) ON CONFLICT(user_id,course_id) DO NOTHING",[student["id"],course_id],conn)
                lessons=query("SELECT l.id FROM lessons l JOIN course_modules m ON m.id=l.module_id WHERE m.course_id=$1 ORDER BY m.position,l.position",[course_id],conn)
                done=round(sample_progress[index]/100*len(lessons))
                for lesson in lessons[:done]:
                    query("INSERT INTO lesson_progress(user_id,lesson_id) VALUES($1,$2) ON CONFLICT DO NOTHING",[student["id"],lesson["id"]],conn)
                progress=round(done/len(lessons)*100) if lessons else 0
                query("UPDATE enrollments SET progress_percent=$1 WHERE user_id=$2 AND course_id=$3",[progress,student["id"],course_id],conn)
                query("INSERT INTO notifications(user_id,title,body,href) SELECT $1,$2,$3,$4 WHERE NOT EXISTS(SELECT 1 FROM notifications WHERE user_id=$1 AND title=$2 AND body=$3)",[student["id"],"Welcome to BharatLearn","Your next learning milestone is ready when you are.","/dashboard"],conn)
            query("INSERT INTO reviews(user_id,course_id,rating,body,is_approved) SELECT u.id,'python-fundamentals',5,'Clear explanations and useful practice. I built confidence one lesson at a time.',true FROM users u WHERE u.email='student1@bharatlearn.in' ON CONFLICT(user_id,course_id) DO NOTHING",conn=conn)
        print(f"Seeded {len(CATEGORIES)} categories, {len(INSTRUCTORS)} instructors, {len(COURSES)} courses, {len(CATEGORIES) * 10} tests and {len(CATEGORIES) * 120} test questions.")
        print(f"Admin: {admin_email} (set SEED_ADMIN_PASSWORD before running seed to change it).")
        if os.getenv("SEED_DEMO_USERS", "true").strip().lower() in {"1", "true", "yes"}:
            print("Demo student: student1@bharatlearn.in / Student123!")
    finally:
        pool.close()


if __name__ == "__main__":
    main()
