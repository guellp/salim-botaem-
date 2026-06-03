/**
 * 살림 Botaem 공식 자바스크립트 (script.js)
 * 기능: 에코 헤더 스크롤 제어, 스크롤 진입 페이드인 모션
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // 1. Sticky Header 제어
    // ==========================================
    const header = document.getElementById('salim-header');
    
    const handleScroll = () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    };

    // 스크롤 이벤트 리스너 등록
    window.addEventListener('scroll', handleScroll);
    handleScroll(); // 초기 로딩 검사


    // ==========================================
    // 2. Intersection Observer 활용 Scroll Reveal
    // ==========================================
    const revealElements = document.querySelectorAll('.scroll-reveal');

    const observerOptions = {
        root: null,
        threshold: 0.1, // 요소가 10% 정도 화면에 보이면 모션 작동
        rootMargin: '0px 0px -50px 0px'
    };

    const revealCallback = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target); // 성능을 위해 한 번 활성화되면 감시 해제
            }
        });
    };

    const observer = new IntersectionObserver(revealCallback, observerOptions);

    revealElements.forEach(element => {
        observer.observe(element);
    });


    // ==========================================
    // 3. 폼 큐레이션 서브밋 인터랙션 피드백
    // ==========================================
    const primaryButtons = document.querySelectorAll('.btn-primary');
    primaryButtons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            console.log(`🌱 [살림 Botaem] 마우스 호버 센서 작동: ${btn.id}`);
        });
    });

});
