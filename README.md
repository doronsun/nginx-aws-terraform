# משימת בית DevOps: NGINX על AWS עם Terraform ו-Docker

## סקירה כללית
הפרויקט מקים תשתית מאובטחת בענן AWS באמצעות Terraform, Docker ו-GitHub Actions. בסיום, תוצג הודעה:

> **yo this is nginx**

כל המשאבים מוקמים כקוד, כולל דיפלוי אוטומטי בלחיצה אחת.

---

## דיאגרמת ארכיטקטורה
![דיאגרמה ארכיטקטונית](diagram.png)

- **VPC**: רשת מבודדת עם סאבנטים ציבוריים ופרטיים
- **ALB**: Load Balancer ציבורי, מאזין ל-HTTP ומפנה ל-EC2
- **EC2**: בסאבנט פרטי, מריץ Docker עם NGINX
- **NAT Gateway**: מאפשר ל-EC2 למשוך Docker images
- **אבטחה**: רק ה-ALB חשוף לאינטרנט; EC2 לא נגיש ישירות

---

## דרישות מקדימות
- חשבון AWS (Free Tier)
- Docker (עם buildx)
- Terraform >= 1.5
- AWS CLI מוגדר (`aws configure`)

---

## שלבי התקנה ודיפלוי

### 1. שיבוט הריפוזיטורי
```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 2. בנייה ודחיפת Docker Image (ל-Multi-Arch)
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t doronsun/custom-nginx:latest --push .
```

### 3. דיפלוי תשתית
```bash
terraform init
terraform apply -auto-approve
```

### 4. גישה לאפליקציה
לאחר apply, העתיקו את הפלט alb_dns_name וגשו בדפדפן:
```
http://<alb_dns_name>
```

---

## אבטחה
- **EC2 בסאבנט פרטי** (ללא public IP, ללא SSH)
- **רק ALB חשוף לאינטרנט** (פורט 80)
- **Security Groups**: ALB פותח 80 לכולם; EC2 פותח 80 רק ל-ALB
- **אין סודות בקוד**

---

## מבנה התיקיות
```
├── main.tf         # תשתית Terraform
├── Dockerfile      # בניית Docker ל-NGINX
├── index.html      # דף NGINX מותאם
├── README.md       # תיעוד
├── .github/workflows/deploy.yml # CI/CD
```

---

## פתרון תקלות
- אם מתקבל 502/504, ודאו שהתמונה פומבית ו-multi-arch.
- השתמשו ב:
  ```
  terraform apply -replace="aws_instance.nginx_server" -auto-approve
  ```
  כדי לאלץ יצירת EC2 מחדש.
- בדקו את Target Group ב-AWS Console.

---

## CI/CD עם GitHub Actions
- דיפלוי אוטומטי על push ל-main או develop.
- כולל בניית Docker, דחיפה ל-Docker Hub, Terraform Plan & Apply.
- נדרש להגדיר סודות:
  - `DOCKERHUB_USERNAME` - שם משתמש Docker Hub
  - `DOCKERHUB_TOKEN` - טוקן גישה ל-Docker Hub
  - `AWS_OIDC_ROLE_ARN` - ARN של רול AWS עם הרשאות מתאימות

---

## רישיון
MIT 
