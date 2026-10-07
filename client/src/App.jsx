import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { lazy, Suspense, useEffect } from 'react';
import { useAuth } from './AuthContext.jsx';
import { Shell, Toast } from './components/Shared.jsx';

const publicPage=(name)=>lazy(()=>import('./pages/PublicPages.jsx').then(m=>({default:m[name]})));
const learnerPage=(name)=>lazy(()=>import('./pages/LearnerPages.jsx').then(m=>({default:m[name]})));
const HomePage=publicPage('HomePage'),CoursesPage=publicPage('CoursesPage'),CourseDetailPage=publicPage('CourseDetailPage'),TestsPage=publicPage('TestsPage'),TestInstructionsPage=publicPage('TestInstructionsPage'),TestAttemptPage=publicPage('TestAttemptPage'),TestResultPage=publicPage('TestResultPage'),AuthPage=publicPage('AuthPage'),ForgotPasswordPage=publicPage('ForgotPasswordPage'),AboutPage=publicPage('AboutPage'),InstructorsPage=publicPage('InstructorsPage'),ContactPage=publicPage('ContactPage'),LegalPage=publicPage('LegalPage'),PricingPage=publicPage('PricingPage'),FAQPage=publicPage('FAQPage'),CertificateVerifyPage=publicPage('CertificateVerifyPage');
const DashboardPage=learnerPage('DashboardPage'),MyLearningPage=learnerPage('MyLearningPage'),WishlistPage=learnerPage('WishlistPage'),TestHistoryPage=learnerPage('TestHistoryPage'),CertificatesPage=learnerPage('CertificatesPage'),NotificationsPage=learnerPage('NotificationsPage'),ProfilePage=learnerPage('ProfilePage'),CourseQuizPage=learnerPage('CourseQuizPage'),LearnPage=learnerPage('LearnPage');
const AdminPage=lazy(()=>import('./pages/AdminPage.jsx').then(m=>({default:m.AdminPage})));

function Protected({ children, admin = false }) {
  const { user, ready } = useAuth(); const location = useLocation();
  if (!ready) return <div className="app-loading"><span className="spinner"/><span>Preparing your learning space...</span></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (admin && user.role !== 'admin') return <Navigate to="/dashboard" replace />;
  return children;
}
function GuestOnly({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="app-loading"><span className="spinner"/><span>Preparing your learning space...</span></div>;
  if (user) return <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />;
  return children;
}
function AdminLoginPage() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="app-loading"><span className="spinner"/><span>Preparing your learning space...</span></div>;
  if (user?.role === 'admin') return <Navigate to="/admin" replace />;
  return <Shell footer={false}><AuthPage mode="login" adminMode/></Shell>;
}
function NotFound(){return <div className="not-found"><span className="eyebrow">404 · LOST YOUR WAY?</span><h1>Every good path<br/>has a <em>new beginning.</em></h1><p>That page isn't here. Let's find the next useful step.</p><a className="button button-dark" href="/">Return home <span>→</span></a></div>;}
function SeoManager(){const {pathname}=useLocation();useEffect(()=>{const titles={'/':'BharatLearn — Learn Today. Build India’s Tomorrow.','/courses':'Courses for your next skill — BharatLearn','/tests':'Practice tests — BharatLearn','/about':'About BharatLearn','/contact':'Connect with BharatLearn','/pricing':'Plans & pricing — BharatLearn','/verify':'Verify a BharatLearn certificate','/faq':'Help centre — BharatLearn','/admin-login':'Admin sign in — BharatLearn'};const pageTitle=titles[pathname]||(pathname.startsWith('/courses/')?'Course details — BharatLearn':pathname.startsWith('/tests/')?'Practice test — BharatLearn':pathname==='/admin'?'Admin studio — BharatLearn':'BharatLearn — Learn Today. Build India’s Tomorrow.');document.title=pageTitle;const description=document.querySelector('meta[name="description"]');if(description)description.content='Build your future with practical, career-ready learning made for India.';},[pathname]);return null;}

export default function App(){return <><Suspense fallback={<div className="app-loading"><span className="spinner"/><span>Loading BharatLearn...</span></div>}><Routes>
  <Route path="/" element={<Shell><HomePage/></Shell>}/>
  <Route path="/courses" element={<Shell><CoursesPage/></Shell>}/>
  <Route path="/courses/:id" element={<Shell><CourseDetailPage/></Shell>}/>
  <Route path="/tests" element={<Shell><TestsPage/></Shell>}/>
  <Route path="/tests/:id" element={<Shell><TestInstructionsPage/></Shell>}/>
  <Route path="/tests/take/:id" element={<Protected><TestAttemptPage/></Protected>}/>
  <Route path="/tests/result/:attemptId" element={<Protected><Shell><TestResultPage/></Shell></Protected>}/>
  <Route path="/login" element={<GuestOnly><Shell footer={false}><AuthPage mode="login"/></Shell></GuestOnly>}/>
  <Route path="/admin-login" element={<AdminLoginPage/>}/>
  <Route path="/signup" element={<GuestOnly><Shell footer={false}><AuthPage mode="signup"/></Shell></GuestOnly>}/>
  <Route path="/forgot-password" element={<Shell footer={false}><ForgotPasswordPage/></Shell>}/>
  <Route path="/about" element={<Shell><AboutPage/></Shell>}/>
  <Route path="/instructors" element={<Shell><InstructorsPage/></Shell>}/>
  <Route path="/contact" element={<Shell><ContactPage/></Shell>}/>
  <Route path="/privacy" element={<Shell><LegalPage kind="privacy"/></Shell>}/>
  <Route path="/terms" element={<Shell><LegalPage kind="terms"/></Shell>}/>
  <Route path="/pricing" element={<Shell><PricingPage/></Shell>}/>
  <Route path="/faq" element={<Shell><FAQPage/></Shell>}/>
  <Route path="/verify" element={<Shell><CertificateVerifyPage/></Shell>}/>
  <Route path="/dashboard" element={<Protected><DashboardPage/></Protected>}/>
  <Route path="/learning" element={<Protected><MyLearningPage/></Protected>}/>
  <Route path="/wishlist" element={<Protected><WishlistPage/></Protected>}/>
  <Route path="/test-history" element={<Protected><TestHistoryPage/></Protected>}/>
  <Route path="/certificates" element={<Protected><CertificatesPage/></Protected>}/>
  <Route path="/notifications" element={<Protected><NotificationsPage/></Protected>}/>
  <Route path="/profile" element={<Protected><ProfilePage/></Protected>}/>
  <Route path="/learn/:courseId/quiz/:quizId" element={<Protected><CourseQuizPage/></Protected>}/>
  <Route path="/learn/:courseId/:lessonId?" element={<Protected><LearnPage/></Protected>}/>
  <Route path="/admin" element={<Protected admin><AdminPage/></Protected>}/>
  <Route path="*" element={<Shell><NotFound/></Shell>}/>
</Routes></Suspense><SeoManager/><Toast/></>;}
