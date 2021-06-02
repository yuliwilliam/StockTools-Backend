# optiondata

## API Routes

### Admin
post('/api/admin/authcode')
{password, days}
1. generate
2. code:expiration:createdAt -> db

post('/api/admin/auth')
{authcode}
1. if code -> createdAt
2. ip:expriation -> db
3. setcookie  {exp: timestamp}
