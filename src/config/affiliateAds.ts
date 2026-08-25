export interface AffiliateProduct {
  id: string;
  name: string;
  description: string;
  href: string;
}

export const affiliateProducts: AffiliateProduct[] = [
  {
    id: "kindle",
    name: "Máy đọc sách Kindle",
    description: "Màn hình dễ chịu hơn khi đọc lâu.",
    href: "https://s.shopee.vn/30nRfye7Mc?share_channel_code=5",
  },
  {
    id: "reading-light",
    name: "Đèn đọc sách",
    description: "Ánh sáng dịu, hợp đọc buổi tối.",
    href: "https://s.shopee.vn/4qF5rTDL5Z?share_channel_code=5",
  },
  {
    id: "blue-light-screen-protector",
    name: "Dán chống ánh sáng xanh",
    description: "Giảm chói khi đọc trên máy tính.",
    href: "https://s.shopee.vn/gPWtmFEFD?share_channel_code=5",
  },
];
