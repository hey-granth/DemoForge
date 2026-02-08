export function Footer() {
    return (
        <footer className="footer">
            <div className="footerInner">
                <div className="footerBrand">
                    DemoForge
                </div>
                <nav className="footerNav">
                    <a
                        href="https://github.com/hey-granth"
                        className="footerLink"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        GitHub
                    </a>
                    <a
                        href="https://linkedin.com/in/granth-agarwal"
                        className="footerLink"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        LinkedIn
                    </a>
                    <a
                        href="https://x.com/heygranth"
                        className="footerLink"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        X
                    </a>
                </nav>
                <div className="footerAttribution">
                    <p className="footerAttributionText">
                        Built by Granth Agarwal
                    </p>
                </div>
            </div>
        </footer>
    );
}
