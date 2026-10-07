import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { ArrowRight, Bell, BookOpen, ChevronDown, Code2, GraduationCap, Heart, LogOut, Menu, Moon, Search, ShieldCheck, Sparkles, Sun, X } from 'lucide-react';
import { useAuth } from '../AuthContext.jsx';
import { api } from '../api.js';
import { useEffect } from 'react';
import { categoryFallback, testCategoryFallback } from '../data.js';
import { useTheme } from '../ThemeContext.jsx';

export function Logo({ small = false }) { return <Link className={`brand ${small ? 'brand-small' : ''}`} to="/"><span className="brand-mark"><GraduationCap size={20} strokeWidth={2.4} /></span><span>Bharat<span>Learn</span></span></Link>; }

export function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';
  return <button type="button" className={`icon-button theme-toggle ${className}`} aria-label={label} title={label} onClick={toggleTheme}>{isDark ? <Sun size={18}/> : <Moon size={18}/>}</button>;
}

export function Header() {
  const { user, signOut } = useAuth(); const [open,setOpen]=useState(false); const [profile,setProfile]=useState(false); const [searchOpen,setSearchOpen]=useState(false); const [searchTerm,setSearchTerm]=useState(''); const [suggestions,setSuggestions]=useState({courses:[],categories:[],instructors:[]}); const [categories,setCategories]=useState([]); const [testCategories,setTestCategories]=useState([]); const [categoriesOpen,setCategoriesOpen]=useState(false); const [testsOpen,setTestsOpen]=useState(false); const navigate=useNavigate();
  useEffect(()=>{if(searchTerm.trim().length<2){setSuggestions({courses:[],categories:[],instructors:[]});return;}const timer=setTimeout(()=>api(`/search?q=${encodeURIComponent(searchTerm.trim())}`).then(setSuggestions).catch(()=>setSuggestions({courses:[],categories:[],instructors:[]})),180);return()=>clearTimeout(timer);},[searchTerm]);
  useEffect(()=>{api('/categories').then(data=>setCategories(data.categories||[])).catch(()=>{});},[]);
  useEffect(()=>{api('/tests').then(data=>setTestCategories([...new Set((data.tests||[]).map(test=>test.category).filter(Boolean))])).catch(()=>setTestCategories(testCategoryFallback));},[]);
  const linkClass=({isActive})=>`nav-link ${isActive?'nav-active':''}`;
  return <header className="site-header"><div className="header-inner"><Logo />
    <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={()=>setOpen(!open)}>{open?<X size={20}/>:<Menu size={20}/>}</button>
    <nav className={`main-nav ${open?'nav-open':''}`} aria-label="Main navigation">
      <NavLink to="/" className={linkClass} onClick={()=>setOpen(false)}>Home</NavLink>
      <div className={`nav-dropdown ${categoriesOpen?'dropdown-open':''}`}>
        <div className="nav-dropdown-main"><NavLink to="/courses" end className={linkClass} onClick={()=>{setOpen(false);setCategoriesOpen(false);setTestsOpen(false);}}>Courses</NavLink><button type="button" className="nav-dropdown-toggle" aria-label="Browse course categories" aria-expanded={categoriesOpen} onClick={()=>{setCategoriesOpen(value=>!value);setTestsOpen(false);}}><ChevronDown size={13}/></button></div>
        <div className="nav-dropdown-menu"><Link to="/courses" onClick={()=>{setOpen(false);setCategoriesOpen(false);}}>All courses</Link>{(categories.length?categories:categoryFallback.map(name=>({name,slug:name.toLowerCase().replaceAll(' ','-')}))).map(category=><Link key={category.slug} to={`/courses?category=${encodeURIComponent(category.slug)}`} onClick={()=>{setOpen(false);setCategoriesOpen(false);}}>{category.name}</Link>)}</div>
      </div>
      <div className={`nav-dropdown ${testsOpen?'dropdown-open':''}`}>
        <div className="nav-dropdown-main"><NavLink to="/tests" end className={linkClass} onClick={()=>{setOpen(false);setTestsOpen(false);setCategoriesOpen(false);}}>Tests</NavLink><button type="button" className="nav-dropdown-toggle" aria-label="Browse test categories" aria-expanded={testsOpen} onClick={()=>{setTestsOpen(value=>!value);setCategoriesOpen(false);}}><ChevronDown size={13}/></button></div>
        <div className="nav-dropdown-menu"><Link to="/tests" onClick={()=>{setOpen(false);setTestsOpen(false);}}>All tests</Link>{(testCategories.length?testCategories:testCategoryFallback).map(category=><Link key={category} to={`/tests?category=${encodeURIComponent(category)}`} onClick={()=>{setOpen(false);setTestsOpen(false);}}>{category}</Link>)}</div>
      </div>
      {user&&<NavLink to="/learning" className={linkClass} onClick={()=>setOpen(false)}>My learning</NavLink>}{user&&<NavLink to="/certificates" className={linkClass} onClick={()=>setOpen(false)}>Certificates</NavLink>}<NavLink to="/about" className={linkClass} onClick={()=>setOpen(false)}>About</NavLink><NavLink to="/contact" className={linkClass} onClick={()=>setOpen(false)}>Contact</NavLink>
    </nav>
    <div className="header-actions"><ThemeToggle/><button className="icon-button search-trigger" aria-label="Search" onClick={()=>{setSearchOpen(!searchOpen);setSearchTerm('');}}><Search size={18}/></button>{searchOpen&&<div className="header-search-panel"><form onSubmit={e=>{e.preventDefault();setSearchOpen(false);navigate(`/courses?search=${encodeURIComponent(searchTerm)}`);}}><Search size={16}/><input autoFocus value={searchTerm} onChange={e=>setSearchTerm(e.target.value)} onKeyDown={e=>e.key==='Escape'&&setSearchOpen(false)} placeholder="Search courses, skills, instructors..."/><button type="button" onClick={()=>setSearchOpen(false)} aria-label="Close search"><X size={15}/></button></form>{searchTerm.length>=2&&<div className="search-suggestions">{suggestions.courses?.map(c=><Link key={c.id} to={`/courses/${c.id}`} onClick={()=>setSearchOpen(false)}><BookOpen size={14}/><span><strong>{c.title}</strong><small>{c.subtitle}</small></span><ArrowRight size={14}/></Link>)}{suggestions.categories?.map(c=><Link key={c.slug} to={`/courses?category=${c.slug}`} onClick={()=>setSearchOpen(false)}><Code2 size={14}/><span><strong>{c.name}</strong><small>Course category</small></span><ArrowRight size={14}/></Link>)}{suggestions.instructors?.map(p=><Link key={p.full_name} to={`/instructors`} onClick={()=>setSearchOpen(false)}><GraduationCap size={14}/><span><strong>{p.full_name}</strong><small>{p.title}</small></span><ArrowRight size={14}/></Link>)}{!suggestions.courses?.length&&!suggestions.categories?.length&&!suggestions.instructors?.length&&<span className="search-no-results">No matches yet. Press Enter to search all courses.</span>}</div>}</div>}
      <Link to="/admin-login" className="header-admin-link"><ShieldCheck size={15}/>Admin</Link>
      {user ? <><Link to="/dashboard" className="header-dashboard">Dashboard</Link><Link to="/notifications" className="icon-button notification-link" aria-label="Notifications"><Bell size={18}/></Link><div className="profile-menu-wrap"><button className="avatar-button" onClick={()=>setProfile(!profile)} aria-label="Profile menu">{user.name.split(' ').map(n=>n[0]).slice(0,2).join('')}</button>{profile&&<div className="profile-popover"><div className="profile-popover-name">{user.name}</div><Link to="/profile" onClick={()=>setProfile(false)}>Profile & settings</Link>{user.role==='admin'&&<Link to="/admin" onClick={()=>setProfile(false)}>Admin studio</Link>}<button onClick={()=>{signOut();setProfile(false);navigate('/');}}> <LogOut size={15}/> Sign out</button></div>}</div></> : <><Link className="header-login" to="/login">Log in</Link><Link className="button button-dark button-small" to="/signup">Get started <ArrowRight size={15}/></Link></>}
    </div>
  </div></header>;
}

export function Footer() {
  return <footer className="site-footer"><div className="footer-grid"><div className="footer-brand"><Logo/><p>Practical learning for the people shaping India's next chapter.</p><div className="footer-social">{['LinkedIn','Instagram','YouTube','GitHub'].map(x=><a href="https://example.com" key={x} onClick={e=>e.preventDefault()}>{x}</a>)}</div></div><div><h4>Explore</h4><Link to="/courses">All courses</Link><Link to="/tests">Practice tests</Link><Link to="/pricing">Plans & pricing</Link><Link to="/verify">Verify a certificate</Link></div><div><h4>BharatLearn</h4><Link to="/about">Our story</Link><Link to="/instructors">Instructors</Link><Link to="/contact">Contact</Link><Link to="/faq">FAQs</Link></div><div className="footer-news"><div className="footer-label"><Sparkles size={16}/> Learn with purpose</div><h3>Your next skill starts here.</h3><p>Join a growing community learning by doing.</p><Link className="button button-light button-small" to="/courses">Explore courses <ArrowRight size={15}/></Link></div></div><div className="footer-bottom"><span>© BharatLearn 2026. Built for India's tomorrow.</span><div><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><span>Made with care in India <span className="india-dot">●</span></span></div></div></footer>;
}

export function Shell({ children, footer = true }) { return <><Header/><main>{children}</main>{footer&&<Footer/>}</>; }

export function CourseArtwork({ course, large = false }) {
  const iconMap={Python:'Py',JavaScript:'JS',Java:'J',AI:'✳','Artificial Intelligence':'✳','Data Science':'∑','Data Analytics':'↗','UI/UX':'◒','Full Stack Development':'</>','Web Development':'{ }',DevOps:'⌘'};
  const category=course?.category||'Technology';const glyph=iconMap[category]||iconMap[course?.category_slug]||'✦';
  return <div className={`course-art art-${course?.accent||'orange'} ${large?'course-art-large':''}`} aria-label={`${category} course artwork`}><span className="art-orbit orbit-one"/><span className="art-orbit orbit-two"/><span className="art-glyph">{glyph}</span><span className="art-caption">{category.toUpperCase()}</span><span className="art-spark">✳</span></div>;
}

export function CourseCard({ course, compact = false, wishlisted = false, onWishlist }) {
  const navigate=useNavigate();
  return <article className={`course-card ${compact?'course-card-compact':''}`}><button className={`wishlist-button ${wishlisted?'is-saved':''}`} aria-label={wishlisted?'Remove from wishlist':'Add to wishlist'} onClick={(e)=>{e.preventDefault();onWishlist?.(course.id);}}><Heart size={17} fill={wishlisted?'currentColor':'none'}/></button><button className="course-card-top" onClick={()=>navigate(`/courses/${course.id}`)}><CourseArtwork course={course}/><span className="course-level">{course.level||'Beginner'}</span></button><div className="course-card-body"><span className="eyebrow course-category">{course.category||course.category_name||'Technology'}</span><Link to={`/courses/${course.id}`} className="course-card-title">{course.title}</Link><p className="course-instructor"><span className="mini-avatar">{(course.instructor||'BharatLearn').split(' ').map(n=>n[0]).slice(0,2).join('')}</span>{course.instructor||'BharatLearn Faculty'}</p><div className="course-meta"><span><span className="star">★</span> {Number(course.rating||4.8).toFixed(1)}</span><span>{Number(course.student_count||0).toLocaleString('en-IN')} learners</span></div><div className="course-card-bottom"><strong>₹{Number(course.price_inr||0).toLocaleString('en-IN')}</strong>{course.original_price_inr>course.price_inr&&<del>₹{Number(course.original_price_inr).toLocaleString('en-IN')}</del>}<Link to={`/courses/${course.id}`} className="card-arrow" aria-label={`View ${course.title}`}><ArrowRight size={17}/></Link></div></div></article>;
}

export function SectionHeading({ eyebrow, title, description, action, to }) { return <div className="section-heading"><div>{eyebrow&&<span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2>{description&&<p>{description}</p>}</div>{action&&<Link className="text-link" to={to||'/courses'}>{action}<ArrowRight size={16}/></Link>}</div>; }

export function Toast() { const {toast}=useAuth();return toast?<div className={`toast toast-${toast.type}`} role="status">{toast.message}</div>:null; }
export function EmptyState({ icon:Icon=BookOpen, title, body, action, to }) { return <div className="empty-state"><span className="empty-icon"><Icon size={22}/></span><h3>{title}</h3><p>{body}</p>{action&&<Link className="button button-dark button-small" to={to}>{action}<ArrowRight size={15}/></Link>}</div>; }
export function LoadingBlock({ label='Loading...' }) { return <div className="loading-state"><span className="spinner"/><span>{label}</span></div>; }
export function StatCard({ label,value,detail,icon:Icon,accent='orange' }) { return <div className="stat-card"><span className={`stat-icon stat-${accent}`}><Icon size={19}/></span><span className="stat-label">{label}</span><strong>{value}</strong>{detail&&<small>{detail}</small>}</div>; }
export function PageIntro({ eyebrow,title,description,children }) { return <section className="page-intro"><div className="page-intro-inner"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{children}</div></section>; }
