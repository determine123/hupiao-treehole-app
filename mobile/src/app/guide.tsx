import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {Screen,Button,s} from '../lib/ui';
const steps=[
 ['01 · 找到你的讨论','广场可以按版块、关键词筛选。“最新”按发布时间排列；“本周热门”按最近七天的共鸣和公开回复排序；“等待回应”收集还没有公开回复的帖子。'],
 ['02 · 分享一段真实经历','选好版块，用标题说清问题。租房、工作或生活经验建议注明大致区域和适用时间；不要填写具体门牌、联系方式或他人的身份信息。编辑中的草稿会保存在本机。'],
 ['03 · 等待审核','帖子和回复提交后不会立即公开。在“我的帖子”查看待审核状态；管理员通过后大家才看得到。审核暂时没有固定时限，请勿重复提交催审。'],
 ['04 · 给别人一点回应','共鸣表达认同，回复用于交流。共鸣数量不代表真实性。可在“我共鸣过的”和“我参与过的”找回讨论；引用他人的回复时保留上下文。'],
 ['05 · 管理自己的边界','遇到违规内容可举报；屏蔽后不再显示该发言者的内容，在“我的”里可以解除。自己的内容可删除；删除匿名身份会清除关联数据，不能撤销。'],
 ['06 · 帮助内测变得更好','“内测反馈”只有你和管理员能看到。描述操作步骤、预期结果和实际结果；不要填写密钥或隐私信息。管理员的回复会显示在反馈记录里。'],
];
export default function Guide(){return <Screen><Text style={s.title}>第一次来？慢慢逛。</Text><Text style={s.muted}>这里是沪漂人的匿名交流空间，不需要公开真实姓名。</Text>{steps.map(([title,body])=><View style={s.card} key={title}><Text style={s.label}>{title}</Text><Text style={s.text}>{body}</Text></View>)}<Button onPress={()=>router.push('/rules')}>阅读社区约定与隐私说明</Button><Button secondary onPress={()=>router.push('/compose')}>开始一段讨论</Button><Button secondary onPress={()=>router.push('/feedback')}>提交内测反馈</Button></Screen>}
